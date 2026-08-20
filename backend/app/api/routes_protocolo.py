from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List, Dict, Any
from datetime import datetime
from pydantic import BaseModel

from app.core.database import get_db
from app.models.db_models import EscrituraProtocolo, Tramite, Participacion, Cliente

router = APIRouter(prefix="/protocolo", tags=["protocolo"])

class EscrituraCreate(BaseModel):
    tramite_id: int
    tomo: int
    folio_inicio: int
    folio_fin: int
    tipo_acto: str
    fecha_otorgamiento: datetime
    observaciones: str = None

@router.post("/escrituras")
async def registrar_escritura(
    data: EscrituraCreate,
    workspace_id: int = 1, # TODO: extraer del usuario autenticado
    db: AsyncSession = Depends(get_db)
):
    """
    Registra una nueva escritura en el protocolo.
    Calcula automáticamente el número correlativo de escritura para el año en curso.
    """
    anio_actual = data.fecha_otorgamiento.year

    # Obtener el último número de escritura del año para este workspace
    stmt_max_num = select(func.max(EscrituraProtocolo.numero_escritura)).where(
        and_(
            EscrituraProtocolo.workspace_id == workspace_id,
            EscrituraProtocolo.anio == anio_actual
        )
    )
    res = await db.execute(stmt_max_num)
    max_num = res.scalar() or 0
    nuevo_numero = max_num + 1

    nueva_escritura = EscrituraProtocolo(
        workspace_id=workspace_id,
        tramite_id=data.tramite_id,
        numero_escritura=nuevo_numero,
        anio=anio_actual,
        tomo=data.tomo,
        folio_inicio=data.folio_inicio,
        folio_fin=data.folio_fin,
        tipo_acto=data.tipo_acto,
        fecha_otorgamiento=data.fecha_otorgamiento,
        observaciones=data.observaciones
    )

    db.add(nueva_escritura)
    try:
        await db.commit()
        await db.refresh(nueva_escritura)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al guardar la escritura: {str(e)}")

    return {"status": "ok", "numero_escritura": nuevo_numero, "id": nueva_escritura.id}


@router.get("/indice/{anio}")
async def generar_indice_anual(
    anio: int,
    workspace_id: int = 1,
    db: AsyncSession = Depends(get_db)
):
    """
    Genera los datos del Índice Anual de Protocolo exigido por los Colegios de Escribanos.
    Cruza cada escritura con los intervinientes (partes) registradas en su respectivo trámite.
    """
    # 1. Traer todas las escrituras del año, ordenadas por número
    stmt = select(EscrituraProtocolo).where(
        and_(
            EscrituraProtocolo.workspace_id == workspace_id,
            EscrituraProtocolo.anio == anio
        )
    ).order_by(EscrituraProtocolo.numero_escritura.asc())
    
    res = await db.execute(stmt)
    escrituras = res.scalars().all()

    if not escrituras:
        return {"anio": anio, "total": 0, "indice": []}

    indice_data = []

    for esc in escrituras:
        # 2. Por cada escritura, buscar los intervinientes del trámite
        stmt_part = select(Participacion, Cliente).join(
            Cliente, Participacion.cliente_id == Cliente.id
        ).where(Participacion.tramite_id == esc.tramite_id)
        
        res_part = await db.execute(stmt_part)
        participantes_db = res_part.all()
        
        partes = []
        for part, cli in participantes_db:
            partes.append(f"{cli.nombre_completo} ({part.rol})")
        
        indice_data.append({
            "numero_escritura": esc.numero_escritura,
            "fecha": esc.fecha_otorgamiento.strftime("%Y-%m-%d"),
            "tipo_acto": esc.tipo_acto,
            "tomo": esc.tomo,
            "folios": f"{esc.folio_inicio} al {esc.folio_fin}",
            "partes": " - ".join(partes) if partes else "Sin partes registradas"
        })

    return {
        "anio": anio,
        "total": len(indice_data),
        "indice": indice_data
    }
