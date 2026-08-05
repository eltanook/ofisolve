import json
import asyncio
import uuid
from typing import AsyncGenerator, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from loguru import logger
from langchain_core.messages import HumanMessage

from app.api.dependencies import limiter
from app.agents.graph import ofisolve_graph
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

router = APIRouter(tags=["Trámites & Chat Streaming"])

class AprobacionTramite(BaseModel):
    texto_final: str

from app.api.dependencies import get_current_user

@router.post("/{tramite_id}/aprobar")
@router.post("/{tramite_id}/aprobar/")
@limiter.limit("5/minute")
async def aprobar_tramite(
    request: Request,
    tramite_id: int,
    payload: AprobacionTramite,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user)
):
    """Finaliza un trámite (HITL). Persiste el texto final y cierra el estado."""
    from app.models.db_models import Tramite
    from sqlalchemy import select

    logger.info(f"Aprobando trámite {tramite_id}...")

    stmt = select(Tramite).where(Tramite.id == tramite_id)
    res = await db.execute(stmt)
    tramite = res.scalars().first()

    if not tramite:
        raise HTTPException(status_code=404, detail="Trámite no encontrado")
        
    if tramite.workspace_id != user.workspace_id:
        raise HTTPException(status_code=403, detail="No tiene permisos sobre este trámite (Tenant Isolation)")

    # 1. Generar DOCX definitivo
    from app.services.document_service import DocumentService
    doc_svc = DocumentService()
    
    # Obtener nombre del escribano desde el workspace (o defaults si falla)
    from app.models.db_models import Workspace
    workspace_stmt = select(Workspace).where(Workspace.id == tramite.workspace_id)
    ws_res = await db.execute(workspace_stmt)
    workspace = ws_res.scalars().first()
    
    datos_docx = {
        "texto_certificacion": payload.texto_final,
        "tipo_certificacion_display": "DOCUMENTO NOTARIAL (APROBADO)",
        "nombre_escribano": workspace.nombre if workspace else "N/A",
        "nro_registro": "N/A", # idealmente sacar del usuario
    }
    
    ruta_docx = doc_svc.generar_docx(
        datos_finales=datos_docx,
        nombre_plantilla="certificacion_generica.docx"
    )
    
    # 2. Persistir en base de datos
    from app.models.db_models import DocumentoLibreria
    import datetime
    
    nuevo_doc = DocumentoLibreria(
        workspace_id=tramite.workspace_id,
        tramite_id=tramite.id,
        cliente_id=tramite.cliente_id,
        nombre=ruta_docx.name,
        tipo="docx",
        path=str(ruta_docx),
        is_generated=True,
        fecha_subida=datetime.datetime.utcnow()
    )
    
    try:
        db.add(nuevo_doc)
        tramite.estado = "completado"
        await db.commit()
    except Exception as e:
        await db.rollback()
        import os
        if os.path.exists(ruta_docx):
            os.remove(ruta_docx)
            logger.warning(f"Rollback ACID activado. Archivo {ruta_docx.name} eliminado del disco para evitar leaks.")
        raise HTTPException(status_code=500, detail="Error en Base de Datos. Cambios revertidos para proteger la integridad.")

    return {
        "status": "success",
        "tramite_id": tramite_id,
        "mensaje": "Trámite cerrado y archivado correctamente"
    }

class MoverTramiteInput(BaseModel):
    cliente_id_destino: Optional[int]

@router.patch("/{tramite_id}/mover")
async def mover_tramite(
    tramite_id: int,
    payload: MoverTramiteInput,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user)
):
    """Mueve una carpeta (trámite) a otro cliente."""
    from app.models.db_models import Tramite
    from sqlalchemy import select
    
    stmt = select(Tramite).where(Tramite.id == tramite_id)
    result = await db.execute(stmt)
    tramite = result.scalars().first()
    
    if not tramite:
        raise HTTPException(status_code=404, detail="Trámite no encontrado")
        
    if tramite.workspace_id != user.workspace_id:
        raise HTTPException(status_code=403, detail="Acceso denegado")
        
    tramite.cliente_id = payload.cliente_id_destino
    await db.commit()
    return {"status": "ok", "cliente_id": tramite.cliente_id}


# ----------- PARTICIPACIONES -----------

@router.get("/{tramite_id}/participaciones")
@router.get("/{tramite_id}/participaciones/")
async def obtener_participaciones(tramite_id: int, db: AsyncSession = Depends(get_db)):
    """Obtiene los clientes y sus roles vinculados a un trámite."""
    from app.models.db_models import Participacion, Cliente
    from sqlalchemy import select

    stmt = (
        select(Participacion, Cliente.nombre_completo, Cliente.dni)
        .join(Cliente, Participacion.cliente_id == Cliente.id)
        .where(Participacion.tramite_id == tramite_id)
    )

    result = await db.execute(stmt)
    participaciones = []

    for row in result.all():
        p, nombre, dni = row
        participaciones.append({
            "id": p.id,
            "cliente_id": p.cliente_id,
            "nombre": nombre,
            "dni_cuit": dni,
            "rol": p.rol
        })

    return {
        "tramite_id": tramite_id,
        "clientes": participaciones
    }

@router.post("/{tramite_id}/auditoria")
async def ejecutar_auditoria_legal(tramite_id: int, db: AsyncSession = Depends(get_db)):
    """
    Lee los documentos de la carpeta (vía RAG/Librería), los pasa por el LLM 
    para extraer entidades y los devuelve para compararlos en el frontend.
    """
    from app.services.extraction_service import ExtractorService
    from app.services.document_service import DocumentService
    from app.models.db_models import DocumentoLibreria
    from sqlalchemy import select

    # 1. Obtener documentos de la carpeta
    stmt = select(DocumentoLibreria).where(DocumentoLibreria.tramite_id == tramite_id)
    res = await db.execute(stmt)
    docs = res.scalars().all()
    
    if not docs:
        return {"tramite_id": tramite_id, "clientes": [], "mensaje": "No hay documentos para auditar."}
        
    doc_svc = DocumentService()
    textos = []
    
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=4000,
        chunk_overlap=200,
    )
    
    # Chunking semántico y lectura directa sin N+1
    for d in docs[:5]: 
        try:
            contenido = doc_svc.obtener_contenido_fisico(d)
            if contenido and not contenido.startswith("[Error"):
                chunks = text_splitter.split_text(contenido)
                # Tomamos los primeros chunks preservando estructura
                contenido_limitado = "\n".join(chunks[:2])
                textos.append(f"--- Documento: {d.nombre} ---\n{contenido_limitado}")
        except Exception as e:
            logger.error(f"Error procesando documento {d.id} para auditoría: {e}")
            raise HTTPException(status_code=500, detail="Error interno al procesar los documentos.")
            
    if not textos:
        return {"tramite_id": tramite_id, "clientes": [], "mensaje": "No se pudo leer el contenido de los documentos."}
        
    texto_completo = "\n\n".join(textos)
    
    # 2. Ejecutar Extractor
    extractor = ExtractorService()
    resultado = await extractor.auditar_documentos(texto_completo)
    
    return {
        "tramite_id": tramite_id,
        "clientes": resultado.get("clientes", []),
        "tipo_acto": resultado.get("tipo_acto", "Desconocido")
    }

class ParticipacionCreate(BaseModel):
    cliente_id: int
    rol: str


@router.post("/{tramite_id}/participaciones", status_code=status.HTTP_201_CREATED)
async def agregar_participacion(
    tramite_id: int,
    payload: ParticipacionCreate,
    db: AsyncSession = Depends(get_db)
):
    """Vincula un cliente a un trámite con un rol."""
    from app.models.db_models import Participacion, Cliente, Tramite

    t = await db.execute(select(Tramite).where(Tramite.id == tramite_id))
    if not t.scalars().first():
        raise HTTPException(status_code=404, detail="Trámite no encontrado")

    c = await db.execute(select(Cliente).where(Cliente.id == payload.cliente_id))
    cliente = c.scalars().first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    existing = await db.execute(
        select(Participacion).where(
            Participacion.tramite_id == tramite_id,
            Participacion.cliente_id == payload.cliente_id
        )
    )
    if existing.scalars().first():
        raise HTTPException(status_code=409, detail="El cliente ya está vinculado a este trámite")

    nueva = Participacion(tramite_id=tramite_id, cliente_id=payload.cliente_id, rol=payload.rol)
    db.add(nueva)
    await db.commit()
    await db.refresh(nueva)
    return {
        "id": nueva.id,
        "tramite_id": tramite_id,
        "cliente_id": payload.cliente_id,
        "nombre": cliente.nombre_completo,
        "dni_cuit": cliente.dni,
        "rol": nueva.rol,
    }


@router.delete("/{tramite_id}/participaciones/{participacion_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_participacion(tramite_id: int, participacion_id: int, db: AsyncSession = Depends(get_db)):
    """Desvincula un interviniente de un trámite."""
    from app.models.db_models import Participacion

    result = await db.execute(
        select(Participacion).where(
            Participacion.id == participacion_id,
            Participacion.tramite_id == tramite_id
        )
    )
    p = result.scalars().first()
    if not p:
        raise HTTPException(status_code=404, detail="Participación no encontrada")
    await db.delete(p)
    await db.commit()


@router.get("/{tramite_id}/saludo")
async def saludar_tramite(tramite_id: int, db: AsyncSession = Depends(get_db)):
    """
    Genera un saludo contextual al abrir una carpeta.
    (F) Si el LLM no está disponible, genera un resumen basado en datos de la DB
    sin llamar al LLM — nunca falla.
    """
    from app.models.db_models import Tramite, Participacion, Cliente, DocumentoLibreria
    from app.services.llm_service import LLMService
    from sqlalchemy import select

    # 1. Obtener datos del trámite
    result = await db.execute(select(Tramite).where(Tramite.id == tramite_id))
    tramite = result.scalars().first()
    if not tramite:
        raise HTTPException(status_code=404, detail="Trámite no encontrado")

    # 2. Obtener participaciones
    # 2. Obtener participaciones con datos completos
    stmt = (
        select(Participacion, Cliente)
        .join(Cliente, Participacion.cliente_id == Cliente.id)
        .where(Participacion.tramite_id == tramite_id)
    )
    res_p = await db.execute(stmt)
    part_list = []
    for part, cli in res_p.all():
        cli_dict = cli.__dict__
        cli_info = [f"{k}: {v}" for k, v in cli_dict.items() if v and k not in ["_sa_instance_state", "id", "workspace_id", "fecha_creacion", "nombre_completo"]]
        part_list.append(f"{cli.nombre_completo} ({part.rol}) - Detalles: " + ", ".join(cli_info))

    # 3. Obtener documentos de la carpeta
    res_docs = await db.execute(
        select(DocumentoLibreria).where(DocumentoLibreria.tramite_id == tramite_id)
    )
    docs = res_docs.scalars().all()

    participantes_str = ", ".join(part_list) if part_list else "Sin participantes registrados aún."
    docs_str = ", ".join(d.nombre for d in docs) if docs else "Sin documentos subidos."

    # (F) Resumen sin LLM — siempre disponible
    saludo_fallback = (
        f"📁 **{tramite.nombre}** — {tramite.tipo}\n\n"
        f"**Intervinientes:** {participantes_str}\n"
        f"**Documentos en carpeta:** {docs_str}\n\n"
        f"¿En qué puedo ayudarte con este trámite?"
    )

    # 4. Intentar mejorar el saludo con el LLM (no bloqueante)
    contexto = (
        f"CARPETA: {tramite.nombre}\n"
        f"TIPO: {tramite.tipo}\n"
        f"DESCRIPCIÓN: {tramite.descripcion or 'Sin descripción.'}\n"
        f"INTERVINIENTES: {participantes_str}\n"
        f"DOCUMENTOS: {docs_str}"
    )
    query = (
        "Genera un saludo breve y profesional para el escribano. "
        "Resume el estado de la carpeta y propón el próximo paso lógico. "
        "Sé conciso (máximo 3 líneas)."
    )

    try:
        llm = LLMService()
        respuesta = await asyncio.wait_for(
            llm.chat(query=f"{contexto}\n\n{query}", history=[], tags=["saludo_inicial"]),
            timeout=8.0  # timeout de 8 segundos — si Ollama tarda más, usamos el fallback
        )

        # Si la respuesta parece un error de conexión, usar fallback
        if "connection" in respuesta.lower() or "failed" in respuesta.lower() or "error" in respuesta.lower():
            logger.warning(f"LLM retornó error en saludo — usando fallback: {respuesta[:80]}")
            return {"saludo": saludo_fallback}

        return {"saludo": respuesta}

    except asyncio.TimeoutError:
        logger.warning(f"LLM timeout en saludo de tramite {tramite_id} — usando fallback sin LLM")
        return {"saludo": saludo_fallback}
    except Exception as e:
        logger.error(f"Error generando saludo con LLM: {e} — usando fallback")
        return {"saludo": saludo_fallback}


@router.get("/{tramite_id}/archivos")
async def obtener_archivos_tramite(tramite_id: int, db: AsyncSession = Depends(get_db)):
    """Obtiene TODOS los archivos vinculados a un trámite (subidos + generados)."""
    from app.models.db_models import DocumentoLibreria
    from sqlalchemy import select

    stmt = (
        select(DocumentoLibreria)
        .where(DocumentoLibreria.tramite_id == tramite_id)
        .order_by(DocumentoLibreria.fecha_subida.desc())
    )
    result = await db.execute(stmt)
    docs = result.scalars().all()

    return [
        {
            "id": d.id,
            "nombre": d.nombre,
            "tipo": d.tipo,
            "fecha_subida": d.fecha_subida.isoformat(),
            "is_generated": d.is_generated,
        }
        for d in docs
    ]


@router.get("/documentos/{doc_id}/contenido")
async def obtener_contenido_documento(doc_id: int, db: AsyncSession = Depends(get_db)):
    """Obtiene el contenido de texto de un documento para el editor."""
    from app.services.document_service import DocumentService
    doc_svc = DocumentService()

    contenido = await doc_svc.obtener_contenido(db, doc_id)
    if contenido is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado o ilegible")

    return {"id": doc_id, "contenido": contenido}


@router.post("/documentos/{doc_id}/guardar")
async def guardar_documento(doc_id: int, payload: dict, db: AsyncSession = Depends(get_db)):
    """Guarda los cambios realizados en el editor de vuelta al archivo físico."""
    from app.services.document_service import DocumentService
    doc_svc = DocumentService()

    contenido = payload.get("contenido", "")
    success = await doc_svc.guardar_contenido(db, doc_id, contenido)

    if not success:
        raise HTTPException(status_code=500, detail="Error al guardar el archivo")

    return {"status": "success", "message": "Documento guardado correctamente"}


# ----------- DOCUMENTOS GENERADOS -----------

@router.get("/{tramite_id}/documentos-generados")
async def obtener_documentos_generados(tramite_id: int, db: AsyncSession = Depends(get_db)):
    """
    Devuelve los documentos (.docx) reales asociados a un trámite.
    Incluye el contenido para previsualizar en el frontend.
    """
    from app.models.db_models import DocumentoLibreria
    from app.services.document_service import DocumentService
    from sqlalchemy import select

    stmt = (
        select(DocumentoLibreria)
        .where(
            DocumentoLibreria.tramite_id == tramite_id,
            DocumentoLibreria.is_generated == True
        )
        .order_by(DocumentoLibreria.fecha_subida.desc())
    )
    result = await db.execute(stmt)
    docs = result.scalars().all()

    doc_svc = DocumentService()
    response = []
    for d in docs:
        preview = ""
        try:
            contenido = await doc_svc.obtener_contenido(db, d.id)
            preview = (contenido or "")[:300]
        except Exception:
            pass
        response.append({
            "id": d.id,
            "nombre": d.nombre,
            "tipo": d.tipo,
            "fechaGeneracion": d.fecha_subida.isoformat(),
            "contenidoPreview": preview,
            "tramite_id": d.tramite_id,
            "version": getattr(d, "version", 1)
        })
    return response

class GenerarDocumentoRequest(BaseModel):
    nombre: str
    contenido: str

@router.post("/{tramite_id}/documentos-generados", status_code=status.HTTP_201_CREATED)
async def guardar_documento_generado(
    tramite_id: int, 
    request: GenerarDocumentoRequest, 
    db: AsyncSession = Depends(get_db)
):
    """Guarda un documento con is_generated=True"""
    from app.models.db_models import Tramite, DocumentoLibreria
    import os
    import time
    
    # 1. Verificar trámite y obtener cliente
    res_tram = await db.execute(
        select(Tramite).options(joinedload(Tramite.cliente)).where(Tramite.id == tramite_id)
    )
    tramite = res_tram.scalars().first()
    if not tramite:
        raise HTTPException(status_code=404, detail="Trámite no encontrado")
        
    cliente_dni = tramite.cliente.dni if tramite.cliente else "sin_cliente"
        
    # 2. Guardar archivo físico respetando el árbol
    UPLOAD_DIR = os.path.join("uploads", "clientes", cliente_dni, str(tramite_id))
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    timestamp = int(time.time())
    
    # Check if request.nombre already has an extension
    ext = ".txt" if not request.nombre.lower().endswith(".txt") and not request.nombre.lower().endswith(".docx") else ""
    if request.nombre.lower().endswith(".docx"):
        # We don't have a docx generator in this endpoint yet, but the user expects the docx generated by the frontend maybe?
        # Actually, in ingesi-motor, request.contenido is raw text or base64. For now, it's text.
        ext = ""

    secure_filename = f"gen_{timestamp}_{request.nombre}{ext}"
    file_path = os.path.join(UPLOAD_DIR, secure_filename)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(request.contenido)
        
    # 3. Guardar en BD
    nuevo_doc = DocumentoLibreria(
        workspace_id=tramite.workspace_id,
        tramite_id=tramite_id,
        nombre=request.nombre,
        tipo="Generado",
        ruta_archivo=file_path,
        tamanio_bytes=len(request.contenido),
        is_generated=True
    )
    db.add(nuevo_doc)
    await db.commit()
    await db.refresh(nuevo_doc)
    
    return {
        "id": nuevo_doc.id,
        "nombre": nuevo_doc.nombre,
        "tipo": nuevo_doc.tipo,
        "fechaGeneracion": nuevo_doc.fecha_subida.isoformat(),
        "version": getattr(nuevo_doc, "version", 1),
        "contenidoPreview": request.contenido[:300]
    }
