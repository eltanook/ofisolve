from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.dependencies import limiter, RequireRole
from fastapi import Request
from loguru import logger

from app.core.database import get_db
from app.models.db_models import Workspace, Tramite, Cliente, EquipoMiembro
from app.models.workspace_schemas import (
    WorkspaceCreate, WorkspaceResponse, 
    TramiteCreate, TramiteResponse,
    ClienteCreate, ClienteResponse,
    EquipoMiembroCreate, EquipoMiembroResponse,
    LibroRequerimientoCreate,
    LibroRequerimientoResponse,
    MemoriaNotarialCreate,
    MemoriaNotarialResponse
)

router = APIRouter()

# ==========================================================
# WORKSPACES
# ==========================================================

from sqlalchemy.orm import selectinload

@router.get("/", response_model=List[WorkspaceResponse], status_code=status.HTTP_200_OK)
@limiter.limit("20/minute")
async def read_workspaces(request: Request, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """Obtiene todos los workspaces del usuario."""
    # Usamos selectinload para cargar las relaciones y evitar errores de lazy loading en async
    stmt = (
        select(Workspace)
        .options(
            selectinload(Workspace.tramites),
            selectinload(Workspace.clientes),
            selectinload(Workspace.equipo)
        )
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_workspace(request: Request, workspace: WorkspaceCreate, db: AsyncSession = Depends(get_db)):
    """Crea un nuevo workspace."""
    nuevo = Workspace(nombre=workspace.nombre, descripcion=workspace.descripcion)
    db.add(nuevo)
    await db.commit()
    await db.refresh(nuevo)
    return nuevo

@router.patch("/{id}", response_model=WorkspaceResponse)
@limiter.limit("20/minute")
async def update_workspace(request: Request, id: int, workspace_update: dict, db: AsyncSession = Depends(get_db)):
    """Actualiza un workspace de forma parcial (ej: jurisdiccion, nombre)."""
    result = await db.execute(select(Workspace).filter(Workspace.id == id))
    db_ws = result.scalars().first()
    if not db_ws:
        raise HTTPException(status_code=404, detail="Workspace no encontrado")
    
    allowed = {"nombre", "descripcion", "jurisdiccion", "modelo_ia"}
    for key, value in workspace_update.items():
        if key in allowed and hasattr(db_ws, key):
            setattr(db_ws, key, value)
    
    await db.commit()
    await db.refresh(db_ws)
    return db_ws

# ==========================================================
# TRAMITES
# ==========================================================

@router.post("/{workspace_id}/tramites", response_model=TramiteResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def create_tramite(request: Request, workspace_id: int, tramite: TramiteCreate, db: AsyncSession = Depends(get_db)):
    """Añade un tramite a un workspace."""
    result = await db.execute(select(Workspace).filter(Workspace.id == workspace_id))
    workspace = result.scalars().first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace no encontrado")
        
    nuevo_tramite = Tramite(
        workspace_id=workspace_id,
        nombre=tramite.nombre,
        tipo=tramite.tipo,
        estado=tramite.estado,
        cliente_id=tramite.cliente_id,
        asignado_a_id=tramite.asignado_a_id
    )
    db.add(nuevo_tramite)
    await db.commit()
    await db.refresh(nuevo_tramite)
    return nuevo_tramite

@router.get("/{workspace_id}/tramites", response_model=List[TramiteResponse])
@limiter.limit("40/minute")
async def read_tramites(request: Request, workspace_id: int, db: AsyncSession = Depends(get_db)):
    """Lista trámites de un workspace."""
    result = await db.execute(
        select(Tramite)
        .filter(Tramite.workspace_id == workspace_id)
        .options(selectinload(Tramite.asignado_a))
    )
    return result.scalars().all()

@router.patch("/tramites/{id}", response_model=TramiteResponse)
async def update_tramite(id: int, tramite_update: dict, db: AsyncSession = Depends(get_db)):
    """Actualiza un trámite de forma parcial (ej: asignación, estado)."""
    result = await db.execute(select(Tramite).filter(Tramite.id == id))
    db_tramite = result.scalars().first()
    if not db_tramite:
        raise HTTPException(status_code=404, detail="Trámite no encontrado")
    
    allowed = {"nombre", "tipo", "estado", "descripcion", "asignado_a_id", "cliente_id"}
    for key, value in tramite_update.items():
        if key in allowed and hasattr(db_tramite, key):
            setattr(db_tramite, key, value)
    
    await db.commit()
    await db.refresh(db_tramite)
    return db_tramite


@router.delete("/{workspace_id}/tramites/{tramite_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def delete_tramite(
    request: Request, 
    workspace_id: int, 
    tramite_id: int, 
    db: AsyncSession = Depends(get_db),
    user = Depends(RequireRole(["Admin", "Escribano"]))
):
    """Elimina un trámite y todo su historial de chat y documentos asociados."""
    from sqlalchemy import delete as sql_delete
    from app.models.db_models import MensajeChat, DocumentoLibreria

    result = await db.execute(select(Tramite).filter(Tramite.id == tramite_id, Tramite.workspace_id == workspace_id))
    db_tramite = result.scalars().first()
    if not db_tramite:
        raise HTTPException(status_code=404, detail="Trámite no encontrado")

    # Limpiar registros relacionados primero (cascade manual)
    await db.execute(sql_delete(MensajeChat).where(MensajeChat.tramite_id == tramite_id))
    await db.execute(sql_delete(DocumentoLibreria).where(DocumentoLibreria.tramite_id == tramite_id))
    await db.delete(db_tramite)
    
    # Registro de auditoria
    from app.models.db_models import AuditLog
    audit = AuditLog(
        usuario_id=user.id,
        accion="DELETE_TRAMITE",
        entidad="tramite",
        entidad_id=tramite_id,
        detalles=f"Tramite '{db_tramite.nombre}' eliminado por {user.nombre_completo}"
    )
    db.add(audit)
    
    await db.commit()


@router.post("/{workspace_id}/tramites/{tramite_id}/aprobar")
async def aprobar_tramite(workspace_id: int, tramite_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    """Aprobar un trámite y marcar como finalizado."""
    result = await db.execute(select(Tramite).filter(Tramite.id == tramite_id, Tramite.workspace_id == workspace_id))
    db_tramite = result.scalars().first()
    if not db_tramite:
        raise HTTPException(status_code=404, detail="Trámite no encontrado en este workspace")
    
    db_tramite.estado = "finalizado"
    await db.commit()
    return {"status": "success", "message": f"Trámite {tramite_id} aprobado"}

# ==========================================================
# CLIENTES
# ==========================================================

@router.post("/{workspace_id}/clientes", response_model=ClienteResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def create_cliente(request: Request, workspace_id: int, cliente: ClienteCreate, db: AsyncSession = Depends(get_db)):
    """Añade un cliente a un workspace."""
    result = await db.execute(select(Workspace).filter(Workspace.id == workspace_id))
    workspace = result.scalars().first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace no encontrado")
        
    nuevo_cliente = Cliente(
        workspace_id=workspace_id,
        **cliente.model_dump(exclude_unset=True)
    )
    db.add(nuevo_cliente)
    await db.commit()
    await db.refresh(nuevo_cliente)
    return nuevo_cliente

@router.get("/{workspace_id}/clientes", response_model=List[ClienteResponse])
@limiter.limit("40/minute")
async def read_clientes(request: Request, workspace_id: int, db: AsyncSession = Depends(get_db)):
    """Lista clientes de un workspace."""
    result = await db.execute(select(Cliente).filter(Cliente.workspace_id == workspace_id))
    return result.scalars().all()


@router.patch("/{workspace_id}/clientes/{cliente_id}", response_model=ClienteResponse)
async def update_cliente(workspace_id: int, cliente_id: int, update_data: dict, db: AsyncSession = Depends(get_db)):
    """Edita un cliente existente."""
    result = await db.execute(select(Cliente).filter(Cliente.id == cliente_id, Cliente.workspace_id == workspace_id))
    cliente = result.scalars().first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    for key, value in update_data.items():
        if hasattr(cliente, key) and key not in ["id", "workspace_id", "fecha_creacion"]:
            setattr(cliente, key, value)
    await db.commit()
    await db.refresh(cliente)
    return cliente


@router.delete("/{workspace_id}/clientes/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cliente(
    workspace_id: int, 
    cliente_id: int, 
    db: AsyncSession = Depends(get_db),
    user = Depends(RequireRole(["Admin", "Escribano"]))
):
    """Elimina un cliente, todas sus relaciones en cascada y limpia el disco físico (Storage Leak Fix)."""
    result = await db.execute(select(Cliente).filter(Cliente.id == cliente_id, Cliente.workspace_id == workspace_id))
    cliente = result.scalars().first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
    # 1. Recuperar los documentos asociados antes de que cascade los borre de la DB
    from app.models.db_models import DocumentoLibreria
    docs_result = await db.execute(select(DocumentoLibreria).filter(DocumentoLibreria.cliente_id == cliente_id))
    docs_to_delete = docs_result.scalars().all()
    rutas_fisicas = [doc.path for doc in docs_to_delete if doc.path]

    # 2. Borrar cliente (y en cascada DB)
    await db.delete(cliente)
    
    # 3. Registro de auditoria
    from app.models.db_models import AuditLog
    audit = AuditLog(
        usuario_id=user.id,
        accion="DELETE_CLIENTE",
        entidad="cliente",
        entidad_id=cliente_id,
        detalles=f"Cliente '{cliente.nombre_completo}' y {len(rutas_fisicas)} archivos eliminados por {user.nombre_completo}"
    )
    db.add(audit)
    
    # 4. Commit. Si esto falla, los archivos no se tocan.
    await db.commit()
    
    # 5. Si la DB tuvo exito, purgamos el disco duro
    from app.services.workspace_service import WorkspaceService
    for path in rutas_fisicas:
        WorkspaceService.delete_physical_file(path)

# ==========================================================
# EQUIPO (MIEMBROS)
# ==========================================================

@router.post("/{workspace_id}/equipo", response_model=EquipoMiembroResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def create_equipo_miembro(request: Request, workspace_id: int, equipo: EquipoMiembroCreate, db: AsyncSession = Depends(get_db)):
    """Añade un miembro de equipo a un workspace."""
    result = await db.execute(select(Workspace).filter(Workspace.id == workspace_id))
    workspace = result.scalars().first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace no encontrado")
        
    nuevo_miembro = EquipoMiembro(
        workspace_id=workspace_id,
        nombre=equipo.nombre,
        rol=equipo.rol,
        email=equipo.email
    )
    db.add(nuevo_miembro)
    await db.commit()
    await db.refresh(nuevo_miembro)
    return nuevo_miembro

@router.get("/{workspace_id}/equipo", response_model=List[EquipoMiembroResponse])
@limiter.limit("40/minute")
async def read_equipo(request: Request, workspace_id: int, db: AsyncSession = Depends(get_db)):
    """Lista miembros del equipo de un workspace."""
    result = await db.execute(select(EquipoMiembro).filter(EquipoMiembro.workspace_id == workspace_id))
    return result.scalars().all()

# ==========================================================
# DOCUMENTOS (LIBRERÍA) — Delegado a routes_upload.py
# ==========================================================

@router.post("/{workspace_id}/documentos")
async def upload_documento_workspace(
    workspace_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Upload de documentos al workspace. Delega al motor real de upload.
    Acepta multipart/form-data con campo 'file' y 'tramite_id' opcional.
    (Refactorizado para evitar "Fat Routers")
    """
    from fastapi import UploadFile
    from app.services.workspace_service import WorkspaceService

    form = await request.form()
    file: UploadFile = form.get("file")
    tramite_id_raw = form.get("tramite_id")
    tramite_id = int(tramite_id_raw) if tramite_id_raw else None

    try:
        nuevo_doc = await WorkspaceService.upload_document(workspace_id, tramite_id, file, db)
        return {
            "id": nuevo_doc.id,
            "nombre": nuevo_doc.nombre,
            "tipo": nuevo_doc.tipo,
            "workspace_id": workspace_id,
            "tramite_id": tramite_id,
            "path": nuevo_doc.path if hasattr(nuevo_doc, "path") else getattr(nuevo_doc, "ruta_archivo", ""),
            "status": "success"
        }
    except Exception as e:
        logger.error(f"[Upload] Error en WorkspaceService: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/{workspace_id}/documentos")
async def list_documentos_workspace(workspace_id: int, db: AsyncSession = Depends(get_db)):
    """Lista documentos reales del workspace desde SQLite."""
    from app.models.db_models import DocumentoLibreria
    result = await db.execute(
        select(DocumentoLibreria).where(
            DocumentoLibreria.workspace_id == workspace_id,
            DocumentoLibreria.is_generated == False
        )
    )
    docs = result.scalars().all()
    return [
        {
            "id": d.id,
            "titulo": d.nombre,
            "nombre": d.nombre,
            "tipo": d.tipo,
            "fuente": d.path,
            "workspace_id": d.workspace_id,
            "tramite_id": d.tramite_id,
        }
        for d in docs
    ]

# ==========================================================
# LIBRO DE REQUERIMIENTOS
# ==========================================================
from app.models.db_models import LibroRequerimiento

@router.post("/{workspace_id}/libro", response_model=LibroRequerimientoResponse)
async def crear_asiento_libro(workspace_id: int, asiento: LibroRequerimientoCreate, db: AsyncSession = Depends(get_db)):
    nuevo_asiento = LibroRequerimiento(
        workspace_id=workspace_id,
        tramite_id=asiento.tramite_id,
        nro_correlativo=asiento.nro_correlativo,
        tipo_acto=asiento.tipo_acto,
        intervinientes=asiento.intervinientes,
        fojas=asiento.fojas
    )
    db.add(nuevo_asiento)
    await db.commit()
    await db.refresh(nuevo_asiento)
    return nuevo_asiento

@router.get("/{workspace_id}/libro", response_model=List[LibroRequerimientoResponse])
async def listar_libro(workspace_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(LibroRequerimiento)
        .where(LibroRequerimiento.workspace_id == workspace_id)
        .order_by(LibroRequerimiento.nro_correlativo.desc())
    )
    return result.scalars().all()

# ==========================================================
# MEMORIA NOTARIAL
# ==========================================================
from app.models.db_models import MemoriaNotarial

@router.post("/{workspace_id}/memoria", response_model=MemoriaNotarialResponse)
async def crear_regla_memoria(workspace_id: int, regla: MemoriaNotarialCreate, db: AsyncSession = Depends(get_db)):
    nueva_regla = MemoriaNotarial(
        workspace_id=workspace_id,
        preferencia=regla.preferencia,
        categoria=regla.categoria
    )
    db.add(nueva_regla)
    await db.commit()
    await db.refresh(nueva_regla)
    return nueva_regla

@router.get("/{workspace_id}/memoria", response_model=List[MemoriaNotarialResponse])
async def listar_memoria(workspace_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MemoriaNotarial)
        .where(MemoriaNotarial.workspace_id == workspace_id)
        .order_by(MemoriaNotarial.id.asc())
    )
    return result.scalars().all()

@router.delete("/{workspace_id}/memoria/{regla_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_regla_memoria(workspace_id: int, regla_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MemoriaNotarial)
        .filter(MemoriaNotarial.id == regla_id, MemoriaNotarial.workspace_id == workspace_id)
    )
    regla = result.scalars().first()
    if not regla:
        raise HTTPException(status_code=404, detail="Regla no encontrada")
    await db.delete(regla)
    await db.commit()
    return None
