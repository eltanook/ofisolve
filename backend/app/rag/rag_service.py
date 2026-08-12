"""
Servicio RAG (Retrieval-Augmented Generation) con ChromaDB.

Mejoras implementadas:
- (A+D) Colecciones por trámite: normativa global + docs del trámite
- (C) Contexto real: busca en normativa legal Y documentos del trámite activo
- (E) Extracción de texto de PDFs y DOCX via PyMuPDF/python-docx

ChromaDB corre 100% local, embebido en el proceso Python.
Utiliza Ollama para la generación de embeddings soberanos.
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict

import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger

from app.core.config import get_settings
from app.rag.knowledge_base import DOCUMENTOS_RAG

try:
    from flashrank import Ranker, RerankRequest
    HAS_FLASHRANK = True
except ImportError:
    HAS_FLASHRANK = False

# Nombre de la colección global de normativa notarial
GLOBAL_COLLECTION = "normativa_notarial"


def _tramite_collection_name(tramite_id: int) -> str:
    """Genera el nombre de la colección ChromaDB para un trámite específico."""
    return f"tramite_{tramite_id}"


def _extract_text(file_path: str, content_bytes: bytes, filename: str) -> str:
    """
    (E) Extrae texto de un archivo según su tipo.
    Soporta: PDF (PyMuPDF), DOCX (python-docx), TXT, y fallback UTF-8.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext == "pdf":
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(stream=content_bytes, filetype="pdf")
            extracted_text = "\n".join(page.get_text() for page in doc)
            
            # Si el texto es muy corto (probablemente un PDF escaneado) -> Fallback a OCR
            if len(extracted_text.strip().split()) < 30:
                logger.info(f"Texto extraído nativamente muy corto ({len(extracted_text.split())} palabras). Activando OCR Local...")
                import pytesseract
                from pdf2image import convert_from_bytes
                
                # Para Windows, a veces es necesario especificar la ruta. Asumimos que está en el PATH.
                images = convert_from_bytes(content_bytes)
                ocr_text = []
                for i, img in enumerate(images):
                    text = pytesseract.image_to_string(img, lang='spa')
                    ocr_text.append(text)
                return "\n".join(ocr_text)
            
            return extracted_text
        except ImportError as e:
            logger.warning(f"Librería faltante para PDF o OCR: {e} — fallback a UTF-8 decode")
        except Exception as e:
            logger.warning(f"Error extrayendo PDF o ejecutando OCR: {e}")

    elif ext in ("docx", "doc"):
        try:
            import docx
            import io
            document = docx.Document(io.BytesIO(content_bytes))
            return "\n".join(p.text for p in document.paragraphs)
        except ImportError:
            logger.warning("python-docx no disponible — fallback a UTF-8 decode")
        except Exception as e:
            logger.warning(f"Error extrayendo DOCX: {e}")

    # Fallback: intentar como texto plano
    return content_bytes.decode("utf-8", errors="ignore")


class RAGService:
    """
    Servicio de Retrieval-Augmented Generation con ChromaDB local.

    Mantiene:
    - Una colección GLOBAL con normativa notarial argentina.
    - Colecciones POR TRÁMITE con los documentos subidos a cada carpeta.

    La búsqueda de contexto combina ambas fuentes para dar respuestas
    precisas y específicas al caso activo.
    """

    def __init__(self) -> None:
        """Inicializa el motor de vectores ChromaDB local."""
        settings = get_settings()
        self._persist_dir = Path(settings.chroma_persist_dir)
        self._persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(self._persist_dir))
        self._embedding_fn = None
        self._global_collection = None
        self._ranker = None

        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=150,
            separators=["\n\n", "\n", ". ", " "],
            length_function=len,
        )

    def _inicializar_embeddings(self) -> None:
        """Inicializa el modelo de embeddings según el proveedor (lazy)."""
        if self._embedding_fn is not None:
            return

        settings = get_settings()

        try:
            if settings.ai_provider == "ollama":
                logger.info(f"RAG Service: Usando Ollama ({settings.ollama_embedding_model})")
                from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
                import httpx
                
                class CustomOllamaEmbeddingFunction(EmbeddingFunction):
                    def __init__(self, url: str, model_name: str):
                        self._api_url = url
                        self._model_name = model_name
                        self._session = httpx.Client(timeout=300.0) # 5 minutos de timeout
                        
                    def __call__(self, input: Documents) -> Embeddings:
                        texts = input if isinstance(input, list) else [input]
                        embeddings = []
                        for text in texts:
                            resp = self._session.post(
                                self._api_url, 
                                json={"model": self._model_name, "prompt": text}
                            )
                            resp.raise_for_status()
                            embeddings.append(resp.json())
                            
                        return [
                            emb["embedding"] for emb in embeddings if "embedding" in emb
                        ]
                
                self._embedding_fn = CustomOllamaEmbeddingFunction(
                    model_name=settings.ollama_embedding_model,
                    url=f"{settings.ollama_base_url}/api/embeddings"
                )
                logger.info("RAG Service: Embeddings de Ollama (con Timeout 300s) listos.")
            else:
                logger.warning(f"RAG Service: Proveedor '{settings.ai_provider}' no soporta embeddings específicos. Usando default de Chroma.")
        except Exception as e:
            logger.error(f"Error al inicializar embeddings RAG: {str(e)}")
            logger.warning("Revirtiendo a embeddings default de ChromaDB")
            
        if HAS_FLASHRANK and self._ranker is None:
            try:
                # El Ranker descarga y cachea el modelo ONNX automáticamente
                self._ranker = Ranker(model_name="ms-marco-MiniLM-L-6-v2", cache_dir=str(self._persist_dir / "flashrank_cache"))
                logger.info("RAG Service: FlashRank Re-Ranker inicializado.")
            except Exception as e:
                logger.warning(f"RAG Service: No se pudo inicializar FlashRank: {e}")

    def _get_global_collection(self):
        """Retorna (o crea) la colección global de normativa notarial."""
        self._inicializar_embeddings()
        kwargs = {"name": GLOBAL_COLLECTION}
        if self._embedding_fn:
            kwargs["embedding_function"] = self._embedding_fn
        return self._client.get_or_create_collection(**kwargs)

    def _get_tramite_collection(self, tramite_id: int):
        """Retorna (o crea) la colección específica de un trámite."""
        self._inicializar_embeddings()
        kwargs = {"name": _tramite_collection_name(tramite_id)}
        if self._embedding_fn:
            kwargs["embedding_function"] = self._embedding_fn
        return self._client.get_or_create_collection(**kwargs)

    def _get_semantic_cache_collection(self):
        """Retorna (o crea) la colección de caché semántico global."""
        self._inicializar_embeddings()
        kwargs = {"name": "semantic_cache"}
        if self._embedding_fn:
            kwargs["embedding_function"] = self._embedding_fn
        return self._client.get_or_create_collection(**kwargs)

    async def check_semantic_cache(self, query: str, threshold: float = 0.15) -> Optional[str]:
        """
        Revisa si la query ya fue respondida recientemente (similitud muy alta).
        Devuelve la respuesta cacheada o None.
        """
        from fastapi.concurrency import run_in_threadpool
        
        def query_cache():
            cache_col = self._get_semantic_cache_collection()
            if cache_col.count() > 0:
                # Retorna los resultados junto con sus distancias (distances)
                return cache_col.query(query_texts=[query], n_results=1)
            return None

        try:
            res = await run_in_threadpool(query_cache)
            if res and res["documents"] and res["documents"][0]:
                distance = res["distances"][0][0] if "distances" in res and res["distances"] else 0.0
                # L2 distance cutoff
                if distance < threshold:
                    logger.info(f"[Semantic Cache] HIT! Distancia: {distance:.4f}")
                    return res["metadatas"][0][0].get("response")
        except Exception as e:
            logger.warning(f"[Semantic Cache] Fallo en la lectura del caché: {e}")
        return None

    async def save_semantic_cache(self, query: str, response: str) -> None:
        """
        Guarda la query y su respuesta en el caché semántico.
        """
        from fastapi.concurrency import run_in_threadpool
        import hashlib
        
        def save_cache():
            cache_col = self._get_semantic_cache_collection()
            doc_id = hashlib.sha256(query.encode('utf-8')).hexdigest()
            cache_col.add(
                documents=[query],
                metadatas=[{"response": response}],
                ids=[doc_id]
            )

        try:
            await run_in_threadpool(save_cache)
            logger.debug("[Semantic Cache] Nueva entrada guardada.")
        except Exception as e:
            # Ignoramos si ya existe o hay un error
            logger.warning(f"[Semantic Cache] Fallo en escritura: {e}")

    # ------------------------------------------------------------------
    # Ingestión de Normativa Global
    # ------------------------------------------------------------------

    def ingestar_documentos(self, forzar: bool = False) -> int:
        """Ingesta normativa legal en la colección global."""
        collection = self._get_global_collection()
        audit_logger = logger.bind(audit=True)

        if forzar:
            try:
                self._client.delete_collection(GLOBAL_COLLECTION)
                collection = self._get_global_collection()
            except Exception as e:
                logger.warning(f"Error reseteando colección global: {e}")

        count_actual = collection.count()
        if count_actual > 0 and not forzar:
            return count_actual

        total_chunks = 0
        for doc in DOCUMENTOS_RAG:
            chunks = self._splitter.split_text(doc["contenido"])
            ids = [f"{doc['tipo']}_{doc['jurisdiccion']}_{i}" for i in range(len(chunks))]
            metadatas = [
                {
                    "titulo": doc["titulo"],
                    "fuente": doc["fuente"],
                    "tipo": doc["tipo"],
                    "jurisdiccion": doc["jurisdiccion"],
                    "source": "normativa_global",
                }
                for _ in range(len(chunks))
            ]
            collection.add(documents=chunks, ids=ids, metadatas=metadatas)
            total_chunks += len(chunks)

        audit_logger.info("Ingestión global completada", total=total_chunks)
        return total_chunks

    # ------------------------------------------------------------------
    # (A) Indexar documentos de una carpeta/trámite
    # ------------------------------------------------------------------

    def indexar_documento_tramite(
        self,
        tramite_id: int,
        doc_id: int,
        contenido_bytes: bytes,
        nombre: str,
        tipo_doc: str = "documento_usuario",
    ) -> int:
        """
        (A+D) Indexa un documento subido a una carpeta en su colección específica.
        Extrae el texto (E) y lo vectoriza en la colección del trámite.
        """
        # (E) Extraer texto según el tipo de archivo
        texto = _extract_text("", contenido_bytes, nombre)
        if not texto.strip():
            logger.warning(f"No se pudo extraer texto de '{nombre}' — no se indexa en RAG")
            return 0

        collection = self._get_tramite_collection(tramite_id)
        chunks = self._splitter.split_text(texto)
        if not chunks:
            return 0

        ids = [f"tramite_{tramite_id}_doc_{doc_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "tramite_id": str(tramite_id),
                "doc_id": str(doc_id),
                "nombre": nombre,
                "tipo": tipo_doc,
                "source": "documento_tramite",
            }
            for _ in range(len(chunks))
        ]

        try:
            collection.add(documents=chunks, ids=ids, metadatas=metadatas)
            logger.info(f"[RAG] Indexados {len(chunks)} chunks de '{nombre}' en tramite_{tramite_id}")
        except Exception as e:
            logger.error(f"Error indexando documento en tramite_{tramite_id}: {e}")
            return 0

        return len(chunks)

    def eliminar_documento_tramite(self, tramite_id: int, doc_id: int) -> None:
        """Elimina los chunks de un documento de la colección del trámite."""
        try:
            collection = self._get_tramite_collection(tramite_id)
            # ChromaDB permite borrar por where
            collection.delete(where={"doc_id": str(doc_id)})
            logger.info(f"[RAG] Eliminados chunks del doc {doc_id} de tramite_{tramite_id}")
        except Exception as e:
            logger.warning(f"Error eliminando doc {doc_id} de RAG tramite_{tramite_id}: {e}")

    # ------------------------------------------------------------------
    # (C) Búsqueda de Contexto — Global + Por Trámite
    # ------------------------------------------------------------------

    async def buscar_contexto(
        self,
        query: str,
        tramite_id: Optional[int] = None,
        n_resultados: int = 4,
        cliente_tramites: Optional[List[int]] = None,
    ) -> str:
        """
        (C) Busca contexto relevante en:
        1. Normativa legal global (siempre)
        2. Documentos del trámite activo (si se provee tramite_id)
        3. Múltiples trámites del cliente (si se provee cliente_tramites)

        Retorna texto concatenado listo para usar como contexto del LLM.
        Las consultas a ChromaDB se corren en threadpool para no bloquear el Event Loop.
        """
        from fastapi.concurrency import run_in_threadpool
        partes: List[str] = []

        def query_global():
            global_col = self._get_global_collection()
            if global_col.count() > 0:
                return global_col.query(query_texts=[query], n_results=min(15, global_col.count()))
            return None
            
        def query_tramite(t_id: int):
            tramite_col = self._get_tramite_collection(t_id)
            if tramite_col.count() > 0:
                return tramite_col.query(
                    query_texts=[query],
                    n_results=min(15, tramite_col.count()),
                )
            return None

        # Pool de candidatos
        candidatos = []
        
        # 1. Búsqueda en normativa global
        try:
            res = await run_in_threadpool(query_global)
            if res and res["documents"] and res["documents"][0]:
                distances = res.get("distances", [[0.0] * len(res["documents"][0])])[0]
                for i, (doc, meta, dist) in enumerate(zip(res["documents"][0], res["metadatas"][0], distances)):
                    if dist < 0.6:  # Limite más flexible antes del re-rank
                        candidatos.append({
                            "id": f"global_{i}",
                            "text": f"[Normativa — {meta.get('titulo', 'Legal')}]\n{doc}",
                            "meta": meta
                        })
        except Exception as e:
            logger.error(f"Error buscando en normativa global: {e}")

        # 2. Búsqueda en documentos del trámite (si corresponde) o de la lista de trámites
        tramites_a_buscar = []
        if cliente_tramites:
            tramites_a_buscar.extend(cliente_tramites)
        elif tramite_id is not None:
            tramites_a_buscar.append(tramite_id)
            
        for t_id in tramites_a_buscar:
            try:
                res = await run_in_threadpool(query_tramite, t_id)
                if res and res["documents"] and res["documents"][0]:
                    distances = res.get("distances", [[0.0] * len(res["documents"][0])])[0]
                    for i, (doc, meta, dist) in enumerate(zip(res["documents"][0], res["metadatas"][0], distances)):
                        if dist < 0.6:
                            candidatos.append({
                                "id": f"tramite_{t_id}_{i}",
                                "text": f"[Doc. Carpeta (Trámite {t_id}) — {meta.get('nombre', 'Documento')}]\n{doc}",
                                "meta": meta
                            })
            except Exception as e:
                logger.error(f"Error buscando en colección tramite_{t_id}: {e}")

        # 3. Aplicar Re-Ranking con FlashRank si está disponible
        if HAS_FLASHRANK and self._ranker and candidatos:
            try:
                def run_rerank():
                    req = RerankRequest(query=query, passages=candidatos)
                    return self._ranker.rerank(req)
                
                reranked = await run_in_threadpool(run_rerank)
                # Tomar los top n_resultados
                mejores = reranked[:n_resultados]
                partes = [item["text"] for item in mejores]
                top_score = mejores[0].get("score", 0.0) if mejores else 0.0
                logger.info(f"[RAG] Re-Ranking aplicado. Top score: {top_score:.4f} de {len(candidatos)} candidatos.")
            except Exception as e:
                logger.error(f"Error en Re-Ranking: {e}. Fallback a orden original.")
                partes = [c["text"] for c in candidatos[:n_resultados]]
        else:
            # Fallback si no hay flashrank
            partes = [c["text"] for c in candidatos[:n_resultados]]

        return "\n\n---\n\n".join(partes) if partes else ""

    # ------------------------------------------------------------------
    # Compatibilidad hacia atrás (documentos dinámicos globales)
    # ------------------------------------------------------------------

    def agregar_documento_dinamico(
        self,
        contenido: str,
        nombre: str,
        tipo_doc: str = "procedimiento",
        tramite_id: Optional[int] = None,
    ) -> None:
        """
        Agrega un documento al RAG.
        Si se provee tramite_id, lo agrega a la colección del trámite.
        Si no, lo agrega a la colección global (comportamiento legacy).
        """
        if tramite_id is not None:
            # Generar un doc_id temporal basado en timestamp
            doc_id = int(datetime.now().timestamp())
            self.indexar_documento_tramite(
                tramite_id=tramite_id,
                doc_id=doc_id,
                contenido_bytes=contenido.encode("utf-8"),
                nombre=nombre,
                tipo_doc=tipo_doc,
            )
        else:
            # Legacy: agregar a colección global
            try:
                collection = self._get_global_collection()
                chunks = self._splitter.split_text(contenido)
                if not chunks:
                    return
                ids = [f"dinamico_{nombre}_{i}" for i in range(len(chunks))]
                metadatas = [{"titulo": nombre, "fuente": nombre, "tipo": tipo_doc, "jurisdiccion": "usuario"} for _ in chunks]
                collection.add(documents=chunks, ids=ids, metadatas=metadatas)
                logger.info(f"[RAG] Documento dinámico '{nombre}' agregado a normativa global.")
            except Exception as e:
                logger.warning(f"Error agregando documento dinámico: {e}")

    def reset_collection(self) -> bool:
        """Limpia la colección global de normativa."""
        try:
            self._client.delete_collection(GLOBAL_COLLECTION)
            self._embedding_fn = None
            self._global_collection = None
            return True
        except Exception as e:
            logger.error(f"Error reseteando RAG global: {str(e)}")
            return False

    def get_stats(self) -> dict:
        """Estadísticas básicas del sistema RAG."""
        settings = get_settings()
        self._inicializar_embeddings()
        try:
            global_col = self._get_global_collection()
            global_count = global_col.count()
        except Exception:
            global_count = 0

        # ChromaDB v0.6.0+: list_collections retorna strings (nombres)
        try:
            all_collections = self._client.list_collections()
            # Puede retornar strings o objetos según versión
            names = [c if isinstance(c, str) else getattr(c, "name", str(c)) for c in all_collections]
            tramite_collections = [n for n in names if n.startswith("tramite_")]
        except Exception:
            tramite_collections = []

        return {
            "modo": "ChromaDB (local per-tramite)",
            "proveedor_ia": settings.ai_provider,
            "embeddings_activos": self._embedding_fn is not None,
            "normativa_global_chunks": global_count,
            "total_documentos": global_count,
            "colecciones_tramite": len(tramite_collections),
        }
