import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models import db_models, documento_schemas
from app.rag.rag_service import RAGService

router = APIRouter(prefix="/workspaces", tags=["Librería y Carga"])

# Directorio para archivos subidos
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

def _indexar_background(
    tramite_id: Optional[int], 
    doc_id: int, 
    content: bytes, 
    filename: str, 
    tipo: str
):
    """Tarea sincrónica para ejecutar el RAG en segundo plano."""
    try:
        rag_service = RAGService()
        if tramite_id:
            chunks = rag_service.indexar_documento_tramite(
                tramite_id=tramite_id,
                doc_id=doc_id,
                contenido_bytes=content,
                nombre=filename,
                tipo_doc=tipo,
            )
            logger.info(f"Fondo: Documento '{filename}' indexado: {chunks} chunks.")
        else:
            from app.rag.rag_service import _extract_text
            texto = _extract_text("", content, filename)
            rag_service.agregar_documento_dinamico(
                contenido=texto,
                nombre=filename,
                tipo_doc=tipo,
            )
            logger.info(f"Fondo: Documento '{filename}' agregado a RAG global.")
    except Exception as e:
        logger.error(f"Fondo: Error indexando RAG: {e}")

@router.post("/{workspace_id}/documentos", response_model=documento_schemas.DocumentoLibreriaResponse)
async def upload_documento(
    workspace_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    tramite_id: Optional[int] = Form(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: db_models.Usuario = Depends(get_current_user)
):
    """
    Sube un archivo a la librería del workspace.
    (E) Extrae texto del PDF/DOCX.
    (A+D) Lo indexa en la colección ChromaDB del trámite (si se provee tramite_id)
    o en la colección global (fallback).
    """
    # 1. Leer contenido del archivo
    content = await file.read()

    # 2. Guardar físicamente
    safe_name = f"ws_{workspace_id}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)
    with open(file_path, "wb") as buffer:
        buffer.write(content)

    # 3. Registrar en base de datos
    db_doc = db_models.DocumentoLibreria(
        workspace_id=workspace_id,
        tramite_id=tramite_id,
        nombre=file.filename,
        tipo=file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "txt",
        path=file_path
    )
    db.add(db_doc)
    await db.commit()
    await db.refresh(db_doc)

    # 4. (A+E) Indexar en RAG (En segundo plano)
    background_tasks.add_task(
        _indexar_background,
        tramite_id=tramite_id,
        doc_id=db_doc.id,
        content=content,
        filename=file.filename,
        tipo=db_doc.tipo
    )

    return db_doc


@router.get("/{workspace_id}/documentos", response_model=List[documento_schemas.DocumentoLibreriaResponse])
async def listar_documentos(
    workspace_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: db_models.Usuario = Depends(get_current_user)
):
    """Retorna la lista de documentos del workspace."""
    result = await db.execute(
        select(db_models.DocumentoLibreria).filter(
            db_models.DocumentoLibreria.workspace_id == workspace_id
        )
    )
    return result.scalars().all()
