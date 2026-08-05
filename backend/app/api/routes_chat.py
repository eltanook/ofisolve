from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pydantic import BaseModel
from typing import List, Optional
import datetime

from app.core.database import get_db
from app.models.db_models import ChatSession, MensajeChat, Workspace

router = APIRouter(tags=["Chat Global AI"])

class ChatSessionBase(BaseModel):
    titulo: str
    tipo: str = "global"

class ChatSessionCreate(ChatSessionBase):
    pass

class ChatSessionResponse(ChatSessionBase):
    id: int
    workspace_id: int
    fecha_creacion: datetime.datetime

    class Config:
        from_attributes = True

@router.get("/workspaces/{workspace_id}/chat-sessions", response_model=List[ChatSessionResponse])
async def obtener_sesiones(workspace_id: int, db: AsyncSession = Depends(get_db)):
    """Obtiene todas las sesiones de chat de un workspace."""
    stmt = select(ChatSession).where(ChatSession.workspace_id == workspace_id).order_by(ChatSession.fecha_creacion.desc())
    res = await db.execute(stmt)
    return res.scalars().all()

@router.post("/workspaces/{workspace_id}/chat-sessions", response_model=ChatSessionResponse)
async def crear_sesion(workspace_id: int, payload: ChatSessionCreate, db: AsyncSession = Depends(get_db)):
    """Crea una nueva sesión de chat."""
    ws_res = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    if not ws_res.scalars().first():
        raise HTTPException(status_code=404, detail="Workspace no encontrado")
    
    sesion = ChatSession(workspace_id=workspace_id, titulo=payload.titulo, tipo=payload.tipo)
    db.add(sesion)
    await db.commit()
    await db.refresh(sesion)
    return sesion

@router.delete("/workspaces/{workspace_id}/chat-sessions/{session_id}")
async def eliminar_sesion(workspace_id: int, session_id: int, db: AsyncSession = Depends(get_db)):
    """Elimina una sesión de chat y sus mensajes (cascade en DB)."""
    stmt = select(ChatSession).where(ChatSession.id == session_id, ChatSession.workspace_id == workspace_id)
    res = await db.execute(stmt)
    sesion = res.scalars().first()
    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    
    await db.delete(sesion)
    await db.commit()
    return {"status": "ok"}

@router.get("/chat-sessions/{session_id}/mensajes")
async def obtener_mensajes_sesion(session_id: int, db: AsyncSession = Depends(get_db)):
    """Obtiene los mensajes de una sesión."""
    stmt = select(MensajeChat).where(MensajeChat.chat_session_id == session_id).order_by(MensajeChat.timestamp.asc())
    res = await db.execute(stmt)
    mensajes = res.scalars().all()
    return [
        {
            "id": m.id,
            "role": m.role,
            "contenido": m.contenido,
            "timestamp": m.timestamp.isoformat()
        } for m in mensajes
    ]

@router.post("/chat-sessions/{session_id}/mensajes")
async def guardar_mensaje_sesion(session_id: int, payload: dict, db: AsyncSession = Depends(get_db)):
    """Guarda un mensaje en una sesión."""
    mensaje = MensajeChat(
        chat_session_id=session_id,
        role=payload["role"],
        contenido=payload["contenido"]
    )
    db.add(mensaje)
    await db.commit()
    await db.refresh(mensaje)
    return {"status": "ok", "id": mensaje.id}

from fastapi.responses import StreamingResponse
import asyncio
import json

@router.post("/chat-sessions/{session_id}/stream")
async def stream_chat_sesion(session_id: int, payload: dict, db: AsyncSession = Depends(get_db)):
    """
    Recibe el mensaje del usuario y streamea la respuesta del Agente Global de Clientes (React Agent).
    """
    from app.agents.global_client_agent import get_global_client_agent
    from langchain_core.messages import HumanMessage, AIMessage

    mensaje_texto = payload.get("mensaje", "")
    history = payload.get("history", [])
    fuentes_ids = payload.get("fuentes_ids", [])
    
    # Cargar contenido de fuentes si se enviaron
    texto_fuentes = ""
    if fuentes_ids:
        from app.models.db_models import DocumentoLibreria
        from app.services.document_service import DocumentService
        doc_svc = DocumentService()
        stmt_fuentes = select(DocumentoLibreria).where(DocumentoLibreria.id.in_(fuentes_ids))
        res_fuentes = await db.execute(stmt_fuentes)
        docs_fuentes = res_fuentes.scalars().all()
        textos = []
        for d in docs_fuentes:
            contenido = await doc_svc.obtener_contenido(db, d.id)
            if contenido and not contenido.startswith("[Error"):
                textos.append(f"DOCUMENTO ADJUNTO: {d.nombre}\nCONTENIDO:\n{contenido}")
        if textos:
            texto_fuentes = "--- FUENTES EXPRESAMENTE ADJUNTAS POR EL USUARIO ---\n" + "\n\n".join(textos) + "\n\n"

    # Reconstruir historial
    messages = []
    # Limitar historial para no ahogar al modelo
    for msg in history[-10:]:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["contenido"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["contenido"]))
    
    # Agregar el nuevo mensaje con las fuentes si existen
    if texto_fuentes:
        mensaje_final = f"{texto_fuentes}\n{mensaje_texto}"
    else:
        mensaje_final = mensaje_texto
        
    messages.append(HumanMessage(content=mensaje_final))

    agent = get_global_client_agent()
    config = {"configurable": {"thread_id": f"global_client_{session_id}"}}

    async def event_generator():
        try:
            async with asyncio.timeout(120.0):
                # Usamos astream_events para capturar los tokens del LLM y las llamadas a herramientas
                async for event in agent.astream_events({"messages": messages}, config, version="v2"):
                    kind = event["event"]
                    name = event["name"]

                    if kind == "on_chat_model_stream":
                        tags = event.get("tags", [])
                        # Evitar imprimir la salida interna de herramientas
                        if event["data"]["chunk"].content:
                            yield f"data: {json.dumps({'event': 'token', 'texto': event['data']['chunk'].content})}\n\n"
                            
                    elif kind == "on_tool_start":
                        yield f"data: {json.dumps({'event': 'estado', 'nodo': 'Herramienta', 'mensaje': f'Ejecutando: {name}...'})}\n\n"
                    
                    elif kind == "on_tool_end":
                        yield f"data: {json.dumps({'event': 'estado', 'nodo': 'Herramienta', 'mensaje': f'Finalizado: {name}'})}\n\n"

            yield f"data: {json.dumps({'event': 'finalizado'})}\n\n"

        except asyncio.TimeoutError:
            yield f"data: {json.dumps({'event': 'estado', 'nodo': 'Error', 'mensaje': 'Timeout de la IA'})}\n\n"
            yield f"data: {json.dumps({'event': 'finalizado'})}\n\n"
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'event': 'estado', 'nodo': 'Error', 'mensaje': str(e)})}\n\n"
            yield f"data: {json.dumps({'event': 'finalizado'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
