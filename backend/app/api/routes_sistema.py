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
                
                # Priorizar el modelo más potente (Llama) por sobre Qwen para que sea el default
                def get_power_score(m):
                    name = m.lower()
                    if "llama3" in name or "llama-3" in name:
                        return 100
                    if "llama" in name:
                        return 90
                    if "qwen" in name:
                        return 50
                    return 0
                
                modelos.sort(key=get_power_score, reverse=True)
                
                return {"modelos": modelos}
    except Exception:
        pass
    
    # Fallback default models if Ollama fails to respond
    return {"modelos": ["llama3.1", "qwen2.5"]}
