from typing import List, Optional
import datetime
import uuid
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.models.db_models import Cliente, Tramite, Participacion
from app.core.config import get_settings

# ============================================================
# Esquemas Pydantic para Structured Output (Data Entry IA)
# ============================================================

class PersonaExtraida(BaseModel):
    nombre: str = Field(description="Nombre completo de la persona (natural o jurídica)")
    dni_cuit: str = Field(description="DNI o CUIT sin puntos ni guiones")
    rol: str = Field(description="Rol en el trámite (ej: Comprador, Vendedor, Requirente, Autorizante)")
    tipo_persona: str = Field(description="'Fisica' o 'Juridica'", default="Fisica")
    domicilio: Optional[str] = Field(description="Domicilio de la persona si está presente", default=None)
    email: Optional[str] = Field(description="Email de la persona si está presente", default=None)
    telefono: Optional[str] = Field(description="Teléfono de la persona si está presente", default=None)

class ExtraccionNotarial(BaseModel):
    tipo_acto: str = Field(description="Resumen corto del tipo de acto (ej: Venta, Poder, Certificación)")
    personas: List[PersonaExtraida] = Field(description="Lista de personas y sus roles extraídos del texto")

# ============================================================
# Servicio de Extracción Unificado
# ============================================================

class ExtractorService:
    """
    Servicio de extracción de entidades optimizado para Ollama Local.
    """

    def __init__(self, provider: str = "ollama"):
        settings = get_settings()
        
        # Siempre forzamos Ollama para garantizar la soberanía de datos local
        from langchain_ollama import ChatOllama
        self.llm = ChatOllama(
            model=settings.ollama_llm_model,
            base_url=settings.ollama_base_url,
            temperature=0,
            format="json"  # Asegura que Ollama devuelva JSON válido
        )
        logger.info(f"Extractor Service (Ollama Local) listo. Modelo: {settings.ollama_llm_model}")
            
        # El wrapper with_structured_output abstrae la lógica de parseo
        self.extractor = self.llm.with_structured_output(ExtraccionNotarial)

    async def procesar_y_persistir(self, texto: str, db: AsyncSession, workspace_id: int) -> dict:
        """
        Analiza el texto, extrae entidades y realiza el Upsert en SQLite local.
        """
        logger.info(f"[ExtractorService] Analizando para Workspace {workspace_id}...")
        
        # Guardia: si el texto parece ser un mensaje de chat libre (no un documento notarial),
        # no crear un trámite fantasma. Los documentos tienen más de 80 palabras o keywords clave.
        palabras = len(texto.split())
        keywords_doc = ["comparece", "escritura", "escriban", "requirente", "cuit", "matricula", "partió", "certifico"]
        es_doc_notarial = palabras > 80 or any(kw in texto.lower() for kw in keywords_doc)
        
        if not es_doc_notarial:
            logger.info(f"[ExtractorService] Texto parece mensaje de chat libre ({palabras} palabras) — omitiendo extracción.")
            return {"tramite_id": None, "tipo": "chat_libre", "clientes": []}

        try:
            # 1. Llamada al LLM con salida estructurada
            prompt_template = f"""
Eres un experto notarial argentino. Analiza el siguiente documento y extrae los datos requeridos.
REGLAS ESTRICTAS:
- Extrae únicamente personas (físicas o jurídicas) que sean partes principales.
- Si no encuentras un dato (ej. domicilio), déjalo como null, no inventes.

EJEMPLO:
Texto: "Comparece JUAN PEREZ, DNI 12.345.678, soltero, domiciliado en Mitre 123, VENDEDOR..."
Salida: {{"tipo_acto": "Compraventa", "personas": [{{"nombre": "JUAN PEREZ", "dni_cuit": "12345678", "rol": "VENDEDOR", "tipo_persona": "Fisica", "domicilio": "Mitre 123", "email": null, "telefono": null}}]}}

DOCUMENTO A ANALIZAR:
{texto}
"""
            resultado_pydantic: ExtraccionNotarial = await self.extractor.ainvoke(prompt_template)
            
            if not resultado_pydantic:
                logger.warning("[ExtractorService] No se pudieron extraer datos.")
                return {"error": "Extracción fallida"}
            
            # 2. Persistir Trámite
            nuevo_tramite = Tramite(
                workspace_id=workspace_id,
                nombre=f"Trámite: {resultado_pydantic.tipo_acto}",
                tipo=resultado_pydantic.tipo_acto,
                estado="abierto",
                fecha_creacion=datetime.datetime.utcnow()
            )
            db.add(nuevo_tramite)
            await db.flush()

            datos_audit = {
                "tramite_id": nuevo_tramite.id,
                "tipo": nuevo_tramite.tipo,
                "clientes": []
            }

            # 3. Upsert de Clientes y Participaciones
            for p in resultado_pydantic.personas:
                # Búsqueda por DNI (limpiando entrada)
                dni_limpio = "".join(filter(str.isalnum, p.dni_cuit))
                stmt = select(Cliente).where(
                    Cliente.dni == dni_limpio,
                    Cliente.workspace_id == workspace_id
                )
                res = await db.execute(stmt)
                cliente = res.scalars().first()

                if not cliente:
                    logger.info(f"[ExtractorService] Nuevo cliente: {p.nombre}")
                    cliente = Cliente(
                        workspace_id=workspace_id,
                        nombre_completo=p.nombre,
                        dni=dni_limpio,
                        cuit=p.dni_cuit if p.tipo_persona == "Juridica" else None,
                        tipo_persona=p.tipo_persona,
                        domicilio=p.domicilio,
                        email=p.email,
                        telefono=p.telefono
                    )
                    db.add(cliente)
                    await db.flush()
                else:
                    logger.info(f"[ExtractorService] Actualizando existente: {cliente.nombre_completo}")
                    # Actualizar datos si vinieron en la extracción
                    if p.domicilio and not cliente.domicilio: cliente.domicilio = p.domicilio
                    if p.email and not cliente.email: cliente.email = p.email
                    if p.telefono and not cliente.telefono: cliente.telefono = p.telefono
                    cliente.nombre_completo = p.nombre
                    await db.flush()
                
                # Crear Participación
                participacion = Participacion(
                    cliente_id=cliente.id,
                    tramite_id=nuevo_tramite.id,
                    rol=p.rol
                )
                db.add(participacion)
                
                datos_audit["clientes"].append({
                    "id": cliente.id,
                    "nombre": cliente.nombre_completo,
                    "rol": p.rol
                })

            await db.commit()
            logger.info(f"[ExtractorService] Éxito. Trámite ID: {nuevo_tramite.id}")
            return datos_audit

        except Exception as e:
            logger.error(f"[ExtractorService] Error: {str(e)}")
            await db.rollback()
            return {"error": str(e)}

    async def auditar_documentos(self, texto: str) -> dict:
        """
        Analiza el texto de los documentos (RAG) y extrae las entidades,
        sin persistir en BD. Útil para la Auditoría Legal HITL.
        """
        logger.info("[ExtractorService] Ejecutando Auditoría Legal sobre documentos...")
        
        try:
            prompt_template = f"""
Eres un auditor notarial experto. Analiza el siguiente conjunto de documentos y extrae todas las personas/entidades mencionadas y sus roles.
REGLAS ESTRICTAS:
- Extrae únicamente entidades relevantes para el acto notarial.
- Si una persona actúa en representación de otra, identifica correctamente a ambas.

DOCUMENTOS A ANALIZAR:
{texto}
"""
            resultado_pydantic: ExtraccionNotarial = await self.extractor.ainvoke(prompt_template)
            
            if not resultado_pydantic:
                return {"clientes": []}
                
            clientes = []
            for p in resultado_pydantic.personas:
                clientes.append({
                    "nombre": p.nombre,
                    "dni_cuit": p.dni_cuit,
                    "rol": p.rol,
                    "tipo_persona": p.tipo_persona
                })
                
            return {
                "tipo_acto": resultado_pydantic.tipo_acto,
                "clientes": clientes
            }
        except Exception as e:
            logger.error(f"[ExtractorService] Error en auditoría: {str(e)}")
            return {"error": str(e), "clientes": []}

# Para compatibilidad legacy
async def extraer_y_guardar_entidades(texto_contexto: str, db_session: AsyncSession, workspace_id: int) -> dict:
    service = ExtractorService()
    return await service.procesar_y_persistir(texto_contexto, db_session, workspace_id)
