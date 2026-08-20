from fastapi import APIRouter
import httpx
from app.core.config import get_settings

router = APIRouter()
settings = get_settings()

@router.get("/modelos")
async def obtener_modelos():
    """Obtiene los modelos disponibles desde Ollama local."""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get(f"{settings.ollama_base_url}/api/tags")
            if r.status_code == 200:
                data = r.json()
                modelos_raw = [m.get("name") for m in data.get("models", [])]
                # Excluir modelos de embeddings conocidos que no soportan chat
                modelos = [m for m in modelos_raw if "bge-m3" not in m.lower() and "embed" not in m.lower()]
                
                # Asegurar que el modelo principal esté de primero si está presente
                if settings.llm_model in modelos:
                    modelos.remove(settings.llm_model)
                    modelos.insert(0, settings.llm_model)
                
                return {"modelos": modelos}
    except Exception:
        pass
    
    # Fallback default models if Ollama fails to respond
    return {"modelos": [settings.llm_model]}
