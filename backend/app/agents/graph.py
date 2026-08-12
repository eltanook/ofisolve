from typing import Any, Dict, List, Optional, Literal
import uuid
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from loguru import logger
from sqlalchemy import select

from app.agents.state import CertificacionState
from app.services.privacy_service import PrivacyService
from app.services.llm_service import LLMService
from app.services.document_service import DocumentService
from app.rag.rag_service import RAGService
from app.services.extraction_service import ExtractorService
from app.core.database import AsyncSessionLocal
from app.agents.asesor_agent import node_asesor_notarial

async def _get_history(llm_svc, messages) -> List[Dict[str, str]]:
    history = [{"role": "user" if getattr(msg, 'type', 'user') == "human" else "assistant", "content": msg.content} for msg in messages[:-1]]
    if len(history) > 6:
        logger.info("[Agente Memoria] Historial largo detectado. Comprimiendo memoria para proteger VRAM...")
        resumen = await llm_svc.chat(
            query="Resume esta conversación de forma ultra-concisa, manteniendo únicamente los hechos notariales, nombres, documentos mencionados y el estado del trámite.", 
            history=history, 
            tags=["chat_internal"]
        )
        history = [{"role": "assistant", "content": f"[RESUMEN DE MEMORIA PASADA]: {resumen}"}]
    return history

# ==================================================================
# Singletons — servicios pesados se crean una única vez por proceso
# ==================================================================
_rag_service_singleton: RAGService | None = None

def _get_rag_singleton() -> RAGService:
    global _rag_service_singleton
    if _rag_service_singleton is None:
        _rag_service_singleton = RAGService()
    return _rag_service_singleton

# ============================================================
# NODOS DEL GRAFO (Agentes de Grado Empresarial)
# ============================================================

def node_ofuscar(state: CertificacionState) -> dict:
    """Nodo Privacy: Anonimización de PII antes de subir al LLM."""
    logger.info("[Agente Privacy] Iniciando ofuscación de datos... (Bypasseado por entorno local seguro)")
    
    texto_input = ""
    if state.get("messages"):
        last_msg = state["messages"][-1]
        texto_input = last_msg.content if hasattr(last_msg, 'content') else str(last_msg)
    
    # Bypass ofuscación para la app local segura
    ofuscado = {"input": texto_input}
    mapa = {}
    
    return {
        "datos_ofuscados": ofuscado,
        "mapa_inversion": mapa,
        "intentos": 0,
        "aprobado": False
    }

async def node_extractor_erp(state: CertificacionState) -> dict:
    """Nodo ERP: Persistencia Multi-Tenant de entidades extraídas."""
    logger.info("[Agente ERP] Ejecutando Data Entry Automatizado...")
    extractor = ExtractorService()
    
    texto_crudo = state["messages"][-1].content if state["messages"] else ""
    tenant_id_raw = state.get("tenant_id", 1)
    try:
        workspace_id = int(tenant_id_raw)
    except:
        workspace_id = 1
    
    async with AsyncSessionLocal() as db:
        res = await extractor.procesar_y_persistir(
            texto=texto_crudo, 
            db=db, 
            workspace_id=workspace_id
        )
    
    return {
        "datos_extraidos": res,
        "tramite_id": res.get("tramite_id"),
        "workspace_id": workspace_id
    }

async def node_buscar_rag(state: CertificacionState) -> dict:
    """Nodo RAG & Biblioteca: Recuperación de normativa y documentos locales."""
    logger.info(f"[Agente RAG] Consultando base de conocimientos y biblioteca local...")
    rag_svc = _get_rag_singleton()
    
    query = state["messages"][-1].content if state["messages"] else "normativa"
    contexto_legal = await rag_svc.buscar_contexto(query=query, n_resultados=3)
    
    info_biblioteca = ""
    async with AsyncSessionLocal() as db:
        if state.get("tramite_id"):
            from app.models.db_models import DocumentoLibreria
            stmt = select(DocumentoLibreria).where(DocumentoLibreria.tramite_id == state["tramite_id"])
            res = await db.execute(stmt)
            docs = res.scalars().all()
            if docs:
                p_names = [f"- {d.nombre} ({d.tipo})" for d in docs]
                info_biblioteca = "\nDOCUMENTOS DISPONIBLES EN ESTA CARPETA:\n" + "\n".join(p_names)
                logger.info(f"[Agente RAG] Encontrados {len(docs)} documentos en la biblioteca local.")

    return {"contexto_legal": contexto_legal + "\n" + info_biblioteca}

async def node_router(state: CertificacionState, config: dict) -> dict:
    """Nodo Enrutador: Clasifica el trámite para derivarlo a un agente especializado."""
    logger.info("[Agente Router] Clasificando la consulta...")
    
    modo = config.get("configurable", {}).get("modo", "creador")
    if modo == "consultas":
        logger.info("[Agente Router] Modo Consultas detectado.")
        return {"tipo_tramite_detectado": "consultas"}
        
    query = state["messages"][-1].content if state["messages"] else ""
    query_upper = query.upper()
    
    # Lógica Heurística (Extensible luego a clasificación con LLM)
    keywords_escritura = ["COMPRAVENTA", "ESCRITURA", "DONACIÓN", "DONACION", "PODER GENERAL", "HIPOTECA", "INMUEBLE", "SOCIEDAD"]
    keywords_certificacion = ["CERTIFICA", "FIRMA", "FOTOCOPIA", "CERTIFICADO", "COPIA"]
    
    if any(kw in query_upper for kw in keywords_escritura):
        tipo = "escritura"
    elif any(kw in query_upper for kw in keywords_certificacion):
        tipo = "certificacion"
    else:
        tipo = "chat_general"
        
    logger.info(f"[Agente Router] Trámite detectado: {tipo}")
    return {"tipo_tramite_detectado": tipo}

# ============================================================
# RAMA 1: CERTIFICACIONES
# ============================================================

async def node_redactar_certificacion(state: CertificacionState, config: dict) -> dict:
    """Nodo Redactor de Certificaciones (Ligero)."""
    logger.info(f"[Agente Certificaciones] Generando documento (Turno {state.get('intentos', 0) + 1})...")
    modelo_override = config.get("configurable", {}).get("modelo_ia")
    llm_svc = LLMService(modelo_override=modelo_override)
    
    contexto = state.get("contexto_legal", "")
    if state.get("feedback_legal"):
        contexto += f"\n\n[AJUSTE REQUERIDO POR VALIDADOR]: {state['feedback_legal']}"
    
    query = state["messages"][-1].content if state["messages"] else ""
    history = await _get_history(llm_svc, state["messages"])
    
    borrador = await llm_svc.chat(query=query, history=history, contexto_legal=contexto, tags=["chat_stream"])
    return {"texto_generado": borrador, "intentos": state.get("intentos", 0) + 1}

async def node_validar_certificacion(state: CertificacionState, config: dict) -> dict:
    """Validador estándar para certificaciones."""
    logger.info("[Validador Certificaciones] Auditando...")
    texto = state["texto_generado"].upper()
    es_documento_formal = any(kw in texto for kw in ["COMPARECE", "ESCRIBANO", "DOY FE", "CERTIFICO"])
    
    if not es_documento_formal:
        return {"aprobado": True, "feedback_legal": None}

    modelo_override = config.get("configurable", {}).get("modelo_ia")
    llm_svc = LLMService(modelo_override=modelo_override)
    resultado = await llm_svc.validar_documento(state["texto_generado"])
    criticas = resultado.get("criticas", [])
    
    if not resultado.get("aprobado") and state.get("intentos", 0) < 3:
        return {"aprobado": False, "feedback_legal": " ".join(criticas)}
    return {"aprobado": True, "feedback_legal": None}

# ============================================================
# RAMA 2: ESCRITURAS (MEGA PROFESIONAL)
# ============================================================

async def node_redactar_escritura(state: CertificacionState, config: dict) -> dict:
    """Nodo Redactor de Escrituras (Complejo)."""
    logger.info(f"[Agente Escrituras] Generando matriz notarial (Turno {state.get('intentos', 0) + 1})...")
    modelo_override = config.get("configurable", {}).get("modelo_ia")
    llm_svc = LLMService(modelo_override=modelo_override)
    
    # Fetch jurisdicción from DB
    jurisdiccion = "CABA" # Fallback
    tenant_id_raw = state.get("tenant_id", 1)
    try:
        workspace_id = int(tenant_id_raw)
        async with AsyncSessionLocal() as db:
            from app.models.db_models import Workspace
            stmt = select(Workspace).where(Workspace.id == workspace_id)
            res = await db.execute(stmt)
            ws = res.scalar_one_or_none()
            if ws and ws.jurisdiccion:
                jurisdiccion = ws.jurisdiccion
    except Exception as e:
        logger.warning(f"Error buscando jurisdiccion: {e}")

    contexto = state.get("contexto_legal", "")
    contexto += f"\n\n[INSTRUCCIÓN ESTRICTA MEGA PROFESIONAL]: Estás redactando una Escritura Pública para {jurisdiccion}. DEBES incluir obligatoriamente y redactar de forma rigurosa las cláusulas de origen de fondos (UIF), retención impositiva (según corresponda a {jurisdiccion}), y mención de Certificados de Dominio e Inhibición (RPI) con sus números. No omitas ninguna cláusula de estilo notarial."
    if state.get("feedback_legal"):
        contexto += f"\n\n[CORRECCIÓN EXIGIDA POR AUDITORÍA RIGUROSA]: {state['feedback_legal']}"
    
    query = state["messages"][-1].content if state["messages"] else ""
    history = await _get_history(llm_svc, state["messages"])
    
    borrador = await llm_svc.chat(query=query, history=history, contexto_legal=contexto, tags=["chat_stream"])
    return {"texto_generado": borrador, "intentos": state.get("intentos", 0) + 1}

async def node_validar_escritura_rigurosa(state: CertificacionState, config: dict) -> dict:
    """Validador Inteligente (LLM-as-a-Judge) para Escrituras."""
    logger.info("[Validador Escrituras] Auditando Cumplimiento UIF/AFIP/Registros con IA...")
    
    modelo_override = config.get("configurable", {}).get("modelo_ia")
    llm_svc = LLMService(modelo_override=modelo_override)
    
    resultado = await llm_svc.validar_escritura_ia(state["texto_generado"])
    
    if not resultado.get("aprobado") and state.get("intentos", 0) < 3:
        criticas = resultado.get("criticas", [])
        logger.warning(f"[Validador Escrituras] Rechazado por omisiones graves: {criticas}")
        return {
            "aprobado": False, 
            "feedback_legal": " ".join(criticas),
            "requiere_uif": True
        }
    
    logger.info("[Validador Escrituras] Aprobado por el Juez IA.")
    return {"aprobado": True, "feedback_legal": None}

# ============================================================
# RAMA 3: CHAT GENERAL
# ============================================================

async def node_chat_general(state: CertificacionState, config: dict) -> dict:
    logger.info("[Agente Chat] Respondiendo consulta general...")
    modelo_override = config.get("configurable", {}).get("modelo_ia")
    llm_svc = LLMService(modelo_override=modelo_override)
    
    contexto = state.get("contexto_legal", "")
    query = state["messages"][-1].content if state["messages"] else ""
    history = await _get_history(llm_svc, state["messages"])
    
    borrador = await llm_svc.chat(query=query, history=history, contexto_legal=contexto, tags=["chat_stream"])
    return {"texto_generado": borrador, "aprobado": True}

def node_desofuscar(state: CertificacionState) -> dict:
    """Nodo Privacy: Recomposición final con datos reales."""
    logger.info("[Agente Privacy] Reconstruyendo documento con PII real... (Bypasseado)")
    
    texto_vincular = state.get("texto_generado", "")
    
    return {"texto_final": texto_vincular}

# ============================================================
# ORQUESTACIÓN Y COMPILACIÓN
# ============================================================

def router_dispatch(state: CertificacionState) -> Literal["redactar_certificacion", "redactar_escritura", "chat_general", "asesor_notarial"]:
    """Decide a qué agente derivar basado en el tipo detectado."""
    tipo = state.get("tipo_tramite_detectado", "chat_general")
    if tipo == "escritura":
        return "redactar_escritura"
    elif tipo == "certificacion":
        return "redactar_certificacion"
    elif tipo == "consultas":
        return "asesor_notarial"
    return "chat_general"

def decision_certificacion(state: CertificacionState) -> Literal["redactar_certificacion", "desofuscar"]:
    return "desofuscar" if state.get("aprobado") else "redactar_certificacion"

def decision_escritura(state: CertificacionState) -> Literal["redactar_escritura", "desofuscar"]:
    return "desofuscar" if state.get("aprobado") else "redactar_escritura"

def create_advanced_graph():
    """Compila el grafo multi-agente especializado."""
    workflow = StateGraph(CertificacionState)
    
    # Nodos Comunes
    workflow.add_node("ofuscar", node_ofuscar)
    workflow.add_node("extractor_erp", node_extractor_erp)
    workflow.add_node("buscar_rag", node_buscar_rag)
    workflow.add_node("router", node_router)
    workflow.add_node("desofuscar", node_desofuscar)
    
    # Ramas Especializadas
    workflow.add_node("redactar_certificacion", node_redactar_certificacion)
    workflow.add_node("validar_certificacion", node_validar_certificacion)
    
    workflow.add_node("redactar_escritura", node_redactar_escritura)
    workflow.add_node("validar_escritura", node_validar_escritura_rigurosa)
    
    workflow.add_node("chat_general", node_chat_general)
    workflow.add_node("asesor_notarial", node_asesor_notarial)
    
    # Flujo Inicial
    workflow.set_entry_point("ofuscar")
    workflow.add_edge("ofuscar", "extractor_erp")
    workflow.add_edge("extractor_erp", "buscar_rag")
    workflow.add_edge("buscar_rag", "router")
    
    # Enrutamiento Condicional
    workflow.add_conditional_edges("router", router_dispatch)
    
    # Bucle Certificaciones
    workflow.add_edge("redactar_certificacion", "validar_certificacion")
    workflow.add_conditional_edges("validar_certificacion", decision_certificacion)
    
    # Bucle Escrituras
    workflow.add_edge("redactar_escritura", "validar_escritura")
    workflow.add_conditional_edges("validar_escritura", decision_escritura)
    
    # Convergencia de Chat General y Asesor
    workflow.add_edge("chat_general", "desofuscar")
    workflow.add_edge("asesor_notarial", "desofuscar")
    
    # Salida Común
    workflow.add_edge("desofuscar", END)
    
    checkpointer = MemorySaver()
    return workflow.compile(checkpointer=checkpointer)

ofisolve_graph = create_advanced_graph()
