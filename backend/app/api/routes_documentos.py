import json
import asyncio
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.core.database import get_db

from app.api.dependencies import get_current_user
from app.services.context_compressor import ContextCompressor

router = APIRouter(tags=["Documentos & Chat (Por Archivo)"])
context_compressor = ContextCompressor()

class MensajeChatCreate(BaseModel):
    role: str  # "user" | "assistant"
    contenido: str

class MoverDocumentoInput(BaseModel):
    tramite_id_destino: int

@router.patch("/{documento_id}/mover")
async def mover_documento(
    documento_id: int,
    payload: MoverDocumentoInput,
    db: AsyncSession = Depends(get_db)
):
    """Mueve un documento a otro trámite."""
    from app.models.db_models import DocumentoLibreria
    stmt = select(DocumentoLibreria).where(DocumentoLibreria.id == documento_id)
    result = await db.execute(stmt)
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
        
    doc.tramite_id = payload.tramite_id_destino
    await db.commit()
    return {"status": "ok", "tramite_id": doc.tramite_id}

# ----------- HISTORIAL DE CHAT PERMANENTE POR DOCUMENTO -----------

@router.get("/{documento_id}/mensajes")
async def obtener_mensajes(
    documento_id: int, 
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user)
):
    """
    Recupera el historial de chat persistido de un documento verificando tenant.
    """
    from app.models.db_models import MensajeChat, DocumentoLibreria

    # 1. Verificar Tenant Isolation
    doc_res = await db.execute(select(DocumentoLibreria).where(DocumentoLibreria.id == documento_id))
    doc = doc_res.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    if doc.workspace_id != user.workspace_id:
        raise HTTPException(status_code=403, detail="Acceso denegado al documento (Tenant Isolation)")

    stmt = (
        select(MensajeChat)
        .where(MensajeChat.documento_id == documento_id)
        .order_by(MensajeChat.timestamp.asc())
    )
    result = await db.execute(stmt)
    mensajes = result.scalars().all()

    return [
        {
            "id": m.id,
            "role": m.role,
            "contenido": m.contenido,
            "timestamp": m.timestamp.isoformat(),
        }
        for m in mensajes
    ]


@router.post("/{documento_id}/mensajes")
async def guardar_mensaje(
    documento_id: int,
    payload: MensajeChatCreate,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user)
):
    """
    Persiste un mensaje del chat asociado a un documento en la base de datos (con tenant isolation).
    """
    from app.models.db_models import MensajeChat, DocumentoLibreria
    
    # 1. Verificar Tenant Isolation
    doc_res = await db.execute(select(DocumentoLibreria).where(DocumentoLibreria.id == documento_id))
    doc = doc_res.scalars().first()
    if not doc or doc.workspace_id != user.workspace_id:
        raise HTTPException(status_code=403, detail="Acceso denegado")

    mensaje = MensajeChat(
        documento_id=documento_id,
        role=payload.role,
        contenido=payload.contenido,
    )
    db.add(mensaje)
    await db.commit()
    await db.refresh(mensaje)

    return {
        "id": mensaje.id,
        "documento_id": mensaje.documento_id,
        "role": mensaje.role,
        "contenido": mensaje.contenido,
        "timestamp": mensaje.timestamp.isoformat(),
    }


@router.delete("/{documento_id}/mensajes")
async def limpiar_mensajes(documento_id: int, db: AsyncSession = Depends(get_db)):
    """
    Elimina todo el historial de chat de un documento (Refresh/Reset Chat).
    También se encarga de vaciar el thread_id_langgraph si fuera necesario.
    """
    from app.models.db_models import MensajeChat, DocumentoLibreria
    from sqlalchemy import update

    # Eliminar mensajes
    await db.execute(delete(MensajeChat).where(MensajeChat.documento_id == documento_id))
    
    # Resetear el hilo conversacional para LangGraph
    await db.execute(
        update(DocumentoLibreria)
        .where(DocumentoLibreria.id == documento_id)
        .values(thread_id_langgraph=None)
    )
    
    await db.commit()
    return {"status": "ok", "mensaje": "Historial y contexto del documento eliminados exitosamente."}

# ----------- SCHEMAS & STREAMING -----------

import uuid
from typing import AsyncGenerator, Dict, Optional
from fastapi.responses import StreamingResponse
from fastapi import Request
from loguru import logger

from app.api.dependencies import limiter, get_current_user
from app.agents.graph import ofisolve_graph

class ChatInput(BaseModel):
    mensaje: str
    thread_id: str
    tenant_id: str
    history: Optional[List[Dict[str, str]]] = []
    modelo: Optional[str] = None
    modo: Optional[str] = "consultas"  # 'consultas' | 'creador'
    fuentes_ids: Optional[List[int]] = []

NODE_MESSAGES = {
    "ofuscar": "Protegiendo tus datos confidenciales...",
    "extractor_erp": "Extrayendo entidades al centro de trámites...",
    "buscar_rag": "Consultando normativa notarial argentina...",
    "redactar": "Generando borrador notarial...",
    "validar_legalidad": "Auditando cumplimiento y cláusulas...",
    "desofuscar": "Finalizando recomposición del documento..."
}

async def graph_event_generator(
    mensaje: str,
    thread_id: str,
    tenant_id: str,
    history: List[Dict[str, str]] = [],
    workspace_id: Optional[int] = None,
    documento_id: Optional[int] = None,
    modelo_ia: Optional[str] = None,
    modo: str = "consultas",
    fuentes_ids: Optional[List[int]] = None,
) -> AsyncGenerator[str, None]:
    """
    Generador SSE con Soporte de Memoria por Documento.
    Inyecta contexto RAG real del trámite asociado al documento.
    """
    from langchain_core.messages import HumanMessage, AIMessage

    # Obtener el tramite_id a partir del documento para contexto RAG
    from app.models.db_models import DocumentoLibreria, Tramite
    contexto_rag = ""
    tramite_id = None
    cliente_id = None
    cliente_tramites = []

    # Parsear thread_id para ver si estamos a nivel trámite o cliente
    if thread_id.startswith("tramite_"):
        try:
            tramite_id = int(thread_id.split("_")[1])
        except:
            pass
    elif thread_id.startswith("cliente_"):
        try:
            cliente_id = int(thread_id.split("_")[1])
        except:
            pass
            
    if not tramite_id and not cliente_id and documento_id:
        from app.core.database import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            stmt = select(DocumentoLibreria).where(DocumentoLibreria.id == documento_id)
            res = await session.execute(stmt)
            doc = res.scalars().first()
            if doc:
                tramite_id = doc.tramite_id

    try:
        from app.rag.rag_service import RAGService
        from app.services.document_service import DocumentService
        from app.core.database import AsyncSessionLocal
        from app.services.semantic_router import SemanticRouter
        from app.services.memory_service import MemoryService
        
        rag = RAGService()
        doc_svc = DocumentService()
        
        # 1. Caché Semántico
        respuesta_cacheada = await rag.check_semantic_cache(mensaje)
        if respuesta_cacheada:
            logger.info("Devolviendo respuesta desde el caché semántico.")
            yield f"data: {json.dumps({'event': 'estado', 'nodo': 'Cache', 'mensaje': 'Respuesta obtenida del caché'})}\n\n"
            import asyncio
            for word in respuesta_cacheada.split():
                yield f"data: {json.dumps({'event': 'token', 'texto': word + ' '})}\n\n"
                await asyncio.sleep(0.01)
            yield f"data: {json.dumps({'event': 'finalizado', 'texto_completo': respuesta_cacheada})}\n\n"
            return
            
        # 2. Enrutador Semántico
        es_chitchat = SemanticRouter.is_chitchat(mensaje)
        
        if es_chitchat:
            logger.info(f"Mensaje clasificado como Chitchat: '{mensaje}'. Omitiendo RAG.")
            # contexto_rag queda vacío
        else:
            async with AsyncSessionLocal() as session:
                if cliente_id:
                    # Obtener todos los trámites del cliente
                    stmt = select(Tramite).where(Tramite.cliente_id == cliente_id)
                    res = await session.execute(stmt)
                    tramites = res.scalars().all()
                    cliente_tramites = [t.id for t in tramites]
                
                # Cargar FUENTES EXPRESAMENTE ADJUNTAS
                contexto_fuentes = ""
                if fuentes_ids:
                    from app.models.db_models import DocumentoLibreria
                    stmt_fuentes = select(DocumentoLibreria).where(DocumentoLibreria.id.in_(fuentes_ids))
                    res_fuentes = await session.execute(stmt_fuentes)
                    docs_fuentes = res_fuentes.scalars().all()
                    textos_fuentes = []
                    for d in docs_fuentes:
                        contenido = await doc_svc.obtener_contenido(session, d.id)
                        if contenido and not contenido.startswith("[Error"):
                            textos_fuentes.append(f"DOCUMENTO ADJUNTO: {d.nombre}\nCONTENIDO:\n{contenido}")
                    if textos_fuentes:
                        contexto_fuentes = "--- FUENTES EXPRESAMENTE ADJUNTAS POR EL USUARIO ---\n" + "\n\n".join(textos_fuentes) + "\n\n"
                        logger.info(f"Cargadas {len(textos_fuentes)} fuentes expresas para el LLM.")

                if tramite_id or cliente_tramites:
                    # HyDE: Expandir query si es corta
                    query_busqueda = mensaje
                    if len(mensaje.split()) < 15:
                        query_busqueda = await SemanticRouter.expand_query(mensaje)
                        
                    # Buscar en vector DB (normativa global + histórico de los trámites involucrados)
                    contexto_rag = await rag.buscar_contexto(
                        query=query_busqueda,
                        tramite_id=tramite_id,
                        cliente_tramites=cliente_tramites if cliente_tramites else None,
                        n_resultados=4,
                    )
                    
                    # Inyección en vivo: leer documentos reales (LIMITAR a los más relevantes o recientes para no asfixiar a la IA)
                    if tramite_id:
                        stmt = select(DocumentoLibreria).where(DocumentoLibreria.tramite_id == tramite_id).order_by(DocumentoLibreria.fecha_actualizacion.desc()).limit(3)
                    else:
                        stmt = select(DocumentoLibreria).where(DocumentoLibreria.tramite_id.in_(cliente_tramites)).order_by(DocumentoLibreria.fecha_actualizacion.desc()).limit(5)
                        
                    res = await session.execute(stmt)
                    docs = res.scalars().all()
                    textos_vivos = []
                    for d in docs:
                        contenido = await doc_svc.obtener_contenido(session, d.id)
                        if contenido and not contenido.startswith("[Error"):
                            resumen = contenido[:500] + ("..." if len(contenido) > 500 else "")
                            textos_vivos.append(f"DOCUMENTO: {d.nombre}\\nEXTRACTO_INICIAL:\\n{resumen}")
                    
                    # Inyectar datos precisos de los clientes vinculados al trámite
                    contexto_clientes = ""
                    if tramite_id:
                        from app.models.db_models import Participacion, Cliente
                        stmt_cli = select(Participacion.rol, Cliente).join(Cliente, Participacion.cliente_id == Cliente.id).where(Participacion.tramite_id == tramite_id)
                        res_cli = await session.execute(stmt_cli)
                        for rol, cli in res_cli.all():
                            cli_dict = cli.__dict__
                            cli_info = [f"{k}: {v}" for k, v in cli_dict.items() if v and k not in ["_sa_instance_state", "id", "workspace_id", "fecha_creacion"]]
                            contexto_clientes += f"Rol: {rol}\\nDetalles: " + ", ".join(cli_info) + "\\n\\n"
                    
                    if contexto_clientes:
                        contexto_rag = f"--- DATOS DE LOS INTERVINIENTES ---\\n{contexto_clientes}\\n" + contexto_rag

                    if textos_vivos:
                        contexto_vivo = "\\n\\n".join(textos_vivos)
                        # Añadir al inicio del RAG
                        contexto_rag = f"--- DOCUMENTOS ACTUALES ---\\n{contexto_vivo}\\n\\n--- NORMATIVA / OTROS ANTECEDENTES ---\\n{contexto_rag}"
                
                # Prepend fuentes explicitas
                if contexto_fuentes:
                    contexto_rag = contexto_fuentes + contexto_rag
                    
                # Aplicar compresión inteligente para ahorrar contexto y prevenir OOM
                if contexto_rag:
                    contexto_rag = context_compressor.compress(contexto_rag)
                
                # Cargar Memoria a Largo Plazo
                if tenant_id:
                    memoria = await MemoryService.get_workspace_memory(tenant_id, session)
                    if memoria:
                        logger.info("Memoria a largo plazo cargada.")
                        contexto_rag = f"--- MEMORIA DEL USUARIO (PREFERENCIAS) ---\n{memoria}\n\n{contexto_rag}"

    except Exception as e:
        logger.warning(f"RAG context fetch failed (non-critical): {e}")

    import asyncio
    initial_messages = []
    MAX_HISTORY_CHARS = 4000 # Pruning agresivo para no asfixiar a Ollama (OOM)
    current_chars = 0
    
    # Procesar de atrás hacia adelante para conservar lo más reciente
    for msg in reversed((history or [])[-10:]):
        if current_chars > MAX_HISTORY_CHARS:
            break
        msg_content = msg.get("content", msg.get("contenido", ""))[:1000] # Limitar también mensajes individuales largos
        current_chars += len(msg_content)
        
        if msg["role"] == "user":
            initial_messages.insert(0, HumanMessage(content=msg_content))
        elif msg["role"] == "assistant":
            initial_messages.insert(0, AIMessage(content=msg_content))

    mensaje_con_contexto = mensaje
    if contexto_rag:
        mensaje_con_contexto = (
            f"{mensaje}\n\n"
            f"--- CONTEXTO LEGAL Y DOCUMENTAL RELEVANTE ---\n"
            f"{contexto_rag}\n"
            f"--- FIN DEL CONTEXTO ---"
        )

    initial_messages.append(HumanMessage(content=mensaje_con_contexto))

    input_data = {
        "messages": initial_messages,
        "tenant_id": tenant_id,
        "intentos": 0,
        "aprobado": False
    }

    config = {"configurable": {"thread_id": thread_id, "modelo_ia": modelo_ia, "modo": modo}}

    try:
        # Timeout estricto de 120s para abortar si la IA se queda colgada
        async with asyncio.timeout(120.0):
            async for event in ofisolve_graph.astream_events(input_data, config, version="v2"):
                kind = event["event"]
                name = event["name"]

                if kind == "on_chain_start" and name in NODE_MESSAGES:
                    friendly_msg = NODE_MESSAGES[name]
                    yield f"data: {json.dumps({'event': 'estado', 'nodo': name, 'mensaje': friendly_msg})}\n\n"

                elif kind == "on_chat_model_stream":
                    tags = event.get("tags", [])
                    if "chat_stream" in tags:
                        content = event["data"]["chunk"].content
                        if content:
                            yield f"data: {json.dumps({'event': 'token', 'texto': content})}\n\n"

                elif kind == "on_chain_end":
                    if name == "desofuscar":
                        output = event["data"].get("output", {})
                        final_text = output.get("texto_final", "")
                        if final_text:
                            # Guardar en caché semántico (si no fue chitchat puro o es relevante)
                            if not es_chitchat:
                                import asyncio
                                asyncio.create_task(rag.save_semantic_cache(mensaje, final_text))
                                
                            # Extracción de memoria a largo plazo (async)
                            if tenant_id and not es_chitchat:
                                from app.core.database import AsyncSessionLocal
                                from app.services.memory_service import MemoryService
                                import asyncio
                                async def save_mem():
                                    async with AsyncSessionLocal() as db_session:
                                        await MemoryService.extract_and_save_memory(tenant_id, mensaje, final_text, db_session)
                                asyncio.create_task(save_mem())
                                
                            yield f"data: {json.dumps({'event': 'finalizado', 'texto_completo': final_text})}\n\n"
                            
                            # Generar Smart Replies Dinámicas
                            if not es_chitchat:
                                sugerencias = await SemanticRouter.generate_smart_replies(mensaje, final_text)
                                if sugerencias:
                                    yield f"data: {json.dumps({'event': 'sugerencias', 'opciones': sugerencias})}\n\n"
                    elif name == "LangGraph":
                        pass # Prevent sending duplicate finalizado event

    except asyncio.TimeoutError:
        logger.error("[SSE Error] Timeout de IA excedido (120s)")
        yield f"data: {json.dumps({'event': 'error', 'mensaje': 'Tiempo de espera excedido. La IA local está saturada.', 'detalle': 'Timeout'})}\n\n"
    except Exception as e:
        logger.error(f"[SSE Error] {str(e)}")
        # FALLBACK MOCK PARA MODO SIMULADO
        fallback_msg = "Lo siento, el motor IA local no está disponible. [Modo Simulado Activo: Este es un mensaje de prueba para que puedas experimentar la interfaz de chat.]"
        yield f"data: {json.dumps({'event': 'estado', 'nodo': 'IA_Local', 'mensaje': 'Conexión fallida. Usando modo simulado'})}\n\n"
        
        # Simular streaming de tokens
        import asyncio
        for word in fallback_msg.split():
            yield f"data: {json.dumps({'event': 'token', 'texto': word + ' '})}\n\n"
            await asyncio.sleep(0.05)
            
        yield f"data: {json.dumps({'event': 'finalizado', 'texto_completo': fallback_msg})}\n\n"

@router.post("/chat")
@router.post("/chat/")
@limiter.limit("20/minute")
async def chat_documento_stream(
    request: Request,
    payload: ChatInput,
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint principal de comunicación con la IA enfocado en Documentos.
    """
    logger.info(f"Stream iniciado por documento: Tenant {payload.tenant_id} | Hilo {payload.thread_id}")

    # Extraer documento_id del thread_id (formato: "doc_{id}")
    documento_id = None
    if payload.thread_id.startswith("doc_"):
        try:
            documento_id = int(payload.thread_id.split("_")[1])
        except (IndexError, ValueError):
            pass

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no"
    }

    return StreamingResponse(
        graph_event_generator(
            mensaje=payload.mensaje,
            thread_id=payload.thread_id,
            tenant_id=str(payload.tenant_id),
            history=payload.history or [],
            documento_id=documento_id,
            modelo_ia=payload.modelo,
            modo=payload.modo or "consultas",
            fuentes_ids=payload.fuentes_ids
        ),
        headers=headers
    )

@router.post("/{documento_id}/lock")
async def lock_document(documento_id: int, db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
    from app.models.db_models import DocumentoLibreria
    import datetime
    from sqlalchemy import update
    
    stmt = (
        update(DocumentoLibreria)
        .where(
            (DocumentoLibreria.id == documento_id) & 
            ((DocumentoLibreria.locked_by_user_id.is_(None)) | (DocumentoLibreria.locked_by_user_id == user.id))
        )
        .values(
            locked_by_user_id=user.id,
            locked_at=datetime.datetime.utcnow()
        )
        .execution_options(synchronize_session="fetch")
    )
    
    result = await db.execute(stmt)
    await db.commit()
    
    if result.rowcount == 0:
        # Falla porque no existe o está bloqueado por otro
        doc_exists = await db.execute(select(DocumentoLibreria.id).where(DocumentoLibreria.id == documento_id))
        if not doc_exists.scalars().first():
            raise HTTPException(status_code=404, detail="Documento no encontrado")
        raise HTTPException(status_code=403, detail="El documento ya está bloqueado por otro usuario")
        
    return {"status": "locked"}

@router.post("/{documento_id}/unlock")
async def unlock_document(documento_id: int, db: AsyncSession = Depends(get_db), user = Depends(get_current_user)):
    from app.models.db_models import DocumentoLibreria
    
    result = await db.execute(select(DocumentoLibreria).where(DocumentoLibreria.id == documento_id))
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
        
    if doc.locked_by_user_id == user.id or user.rol == "Admin":
        doc.locked_by_user_id = None
        doc.locked_at = None
        await db.commit()
    return {"status": "unlocked"}

# ----------- CONTROL DE VERSIONES Y AUDITORÍA PREVIA -----------

from app.models.documento_schemas import DocumentoVersionResponse, DocumentoVersionCreate

@router.get("/{documento_id}/versiones", response_model=List[DocumentoVersionResponse])
async def obtener_versiones(
    documento_id: int, 
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user)
):
    """
    Obtiene el historial inmutable de versiones de un documento.
    """
    from app.models.db_models import DocumentoLibreria, DocumentoVersion
    doc_res = await db.execute(select(DocumentoLibreria).where(DocumentoLibreria.id == documento_id))
    doc = doc_res.scalars().first()
    if not doc or doc.workspace_id != user.workspace_id:
        raise HTTPException(status_code=404, detail="Documento no encontrado o sin acceso")

    stmt = select(DocumentoVersion).where(DocumentoVersion.documento_id == documento_id).order_by(DocumentoVersion.version.desc())
    versiones = (await db.execute(stmt)).scalars().all()
    return versiones

@router.post("/{documento_id}/control-previo")
async def control_previo_firma(
    documento_id: int,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user)
):
    """
    Simula el motor de Alertas de Control Previo (cotejo registral, cláusulas faltantes).
    Extrae el texto del documento y llama al LLM para analizar inconsistencias.
    """
    from app.models.db_models import DocumentoLibreria
    from app.rag.rag_service import _extract_text
    from app.core.config import get_settings
    from langchain_ollama import ChatOllama
    import os

    doc_res = await db.execute(select(DocumentoLibreria).where(DocumentoLibreria.id == documento_id))
    doc = doc_res.scalars().first()
    if not doc or doc.workspace_id != user.workspace_id:
        raise HTTPException(status_code=404, detail="Documento no encontrado o sin acceso")
    
    if not os.path.exists(doc.path):
         raise HTTPException(status_code=404, detail="Archivo físico no encontrado")

    texto = _extract_text(doc.path, None, os.path.basename(doc.path))
    
    # Usar LLM para detectar cláusulas faltantes
    settings = get_settings()
    llm = ChatOllama(model=settings.ollama_llm_model, base_url=settings.ollama_base_url, temperature=0, format="json")
    
    prompt = f"""
    Eres un Escribano Revisor. Analiza este documento notarial y genera un informe estructurado de "Control Previo a la Firma".
    
    REGLAS ESTRICTAS:
    - Debes detectar si faltan cláusulas obligatorias según la normativa argentina (ej. Origen de fondos UIF, Asentimiento conyugal si corresponde, Asentimiento de convivencia, Lectura de derechos).
    - Revisa discrepancias entre las partes mencionadas.
    - Devuelve estrictamente un JSON válido.

    EJEMPLO DE SALIDA JSON:
    {{
      "alertas": ["Falta declaración jurada sobre si es Persona Expuesta Políticamente (PEP).", "Falta justificación de origen de fondos."],
      "verificaciones_exitosas": ["Comparecencia correcta.", "Fe de conocimiento cumplida."]
    }}
    
    TEXTO DEL DOCUMENTO A REVISAR:
    {texto[:10000]}
    """
    
    try:
        resultado = await llm.ainvoke(prompt)
        import json
        return json.loads(resultado.content)
    except Exception as e:
        return {"error": "Fallo en el control previo automatizado", "detalle": str(e)}
