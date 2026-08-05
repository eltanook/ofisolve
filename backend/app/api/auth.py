from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, Body, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import os
import shutil
import uuid

from app.core.database import get_db
from app.core.security import create_access_token, verify_password, get_password_hash
from app.models.db_models import Usuario, Workspace
from app.models import user_schemas
from app.core.config import get_settings
from app.api.dependencies import get_current_user

router = APIRouter(tags=["Autenticación"])
settings = get_settings()


def _map_user(user: Usuario) -> dict:
    """Mapea un Usuario de la DB al esquema de respuesta."""
    return {
        "id": user.id,
        "email": user.email,
        "nombre_completo": user.nombre_completo,
        "is_active": user.is_active,
        "nro_matricula": user.nro_matricula,
        "escribania_nombre": user.escribania_nombre,
        "avatar_url": user.avatar_url,
        "tenant_id": str(user.workspace_id),
        "workspace_id": user.workspace_id,
    }


@router.post("/login", response_model=user_schemas.Token)
async def login(
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """OAuth2 compatible token login."""
    result = await db.execute(select(Usuario).filter(Usuario.email == form_data.username))
    user = result.scalars().first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Usuario inactivo")

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    return {
        "access_token": create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }


@router.get("/me")
async def read_user_me(
    current_user: Usuario = Depends(get_current_user),
) -> Any:
    """
    Obtener el usuario autenticado actual.
    Verifica el JWT y devuelve los datos del usuario correcto.
    Si no hay token (primer arranque), devuelve el admin por defecto
    sin romper la app.
    """
    return _map_user(current_user)


@router.patch("/me")
async def update_user_me(
    update_data: dict = Body(...),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> Any:
    """Actualiza el perfil del usuario autenticado."""
    allowed_fields = {"nombre_completo", "nro_matricula", "escribania_nombre"}
    for key, value in update_data.items():
        if key in allowed_fields and hasattr(current_user, key):
            setattr(current_user, key, value)

    if "password" in update_data and update_data["password"]:
        current_user.hashed_password = get_password_hash(update_data["password"])

    await db.commit()
    await db.refresh(current_user)
    return _map_user(current_user)


@router.post("/register")
async def register(
    user_in: user_schemas.UserCreate,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """Crear nuevo usuario con su workspace inicial."""
    result = await db.execute(select(Usuario).filter(Usuario.email == user_in.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="El usuario ya existe en este sistema local.")

    nuevo_workspace = Workspace(
        nombre=f"Oficina de {user_in.nombre_completo or 'Nuevo Usuario'}",
        descripcion="Workspace personal creado automáticamente al registrarse."
    )
    db.add(nuevo_workspace)
    await db.flush()

    nuevo_usuario = Usuario(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        nombre_completo=user_in.nombre_completo,
        nro_matricula=user_in.nro_matricula,
        escribania_nombre=user_in.escribania_nombre,
        workspace_id=nuevo_workspace.id,
        rol="Escribano",
        is_active=True
    )
    db.add(nuevo_usuario)
    await db.commit()
    await db.refresh(nuevo_usuario)
    return _map_user(nuevo_usuario)

UPLOAD_AVATAR_DIR = "uploads/avatars"
if not os.path.exists(UPLOAD_AVATAR_DIR):
    os.makedirs(UPLOAD_AVATAR_DIR)

@router.post("/me/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
) -> Any:
    """Sube un avatar para el usuario autenticado."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No se envió ningún archivo")
        
    extension = file.filename.split(".")[-1].lower() if "." in file.filename else "png"
    if extension not in ["jpg", "jpeg", "png", "gif", "webp"]:
        raise HTTPException(status_code=400, detail="Formato no soportado")
    
    filename = f"{current_user.id}_{uuid.uuid4().hex}.{extension}"
    file_path = os.path.join(UPLOAD_AVATAR_DIR, filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    avatar_url = f"/api/v1/auth/avatars/{filename}"
    current_user.avatar_url = avatar_url
    await db.commit()
    await db.refresh(current_user)
    
    return {"avatar_url": avatar_url}

@router.get("/avatars/{filename}")
async def get_avatar(filename: str):
    """Obtiene el avatar público"""
    file_path = os.path.join(UPLOAD_AVATAR_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Avatar no encontrado")
    return FileResponse(file_path)
