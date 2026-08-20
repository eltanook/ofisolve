import re
import json
import httpx
from loguru import logger
from app.core.config import get_settings

class SemanticRouter:
    """
    Enrutador Semántico Ligero.
    Clasifica si una consulta es "Chitchat" (saludos, agradecimientos, interacciones sociales breves)
    o si es una consulta "Transaccional/Jurídica" que requiere acceso a la base documental (RAG).
    """

    CHITCHAT_PATTERNS = [
        r"^(hola|buen[os]?\s*d[ií]as?|buenas\s*tardes?|buenas\s*noches?|holis|holi|buenas)([\s,\.!]*)$",
        r"^(gracias|muchas\s*gracias|te\s*agradezco|excelente|genial|perfecto)([\s,\.!]*)$",
        r"^(chau|adi[oó]s|nos\s*vemos|hasta\s*luego|hasta\s*mañana)([\s,\.!]*)$",
        r"^(c[oó]mo\s*est[aá]s\??|qu[eé]\s*tal\??|todo\s*bien\??)([\s,\.!]*)$"
    ]

    @classmethod
    def is_chitchat(cls, query: str) -> bool:
        """
        Determina si una query es de tipo chitchat (saludos, gracias).
        """
        text = query.strip().lower()
        
        # Si es demasiado largo, probablemente no es solo un saludo.
        if len(text) > 50:
            return False

        for pattern in cls.CHITCHAT_PATTERNS:
            if re.match(pattern, text):
                return True
                
        return False

    @classmethod
    async def expand_query(cls, query: str) -> str:
        """
        (HyDE simplificado) Expande una consulta informal a lenguaje jurídico
        para mejorar la búsqueda en la base documental.
        """
        settings = get_settings()
        if settings.ai_provider != "ollama":
            return query
            
        prompt = f"Reformulá la siguiente consulta informal de un cliente de escribanía a los términos jurídicos formales exactos de la ley argentina para poder buscar antecedentes documentales. Solo devolvé los términos técnicos, nada más. Consulta: '{query}'"
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    f"{settings.ollama_base_url}/api/generate",
                    json={
                        "model": settings.llm_model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.1, "num_ctx": 256}
                    }
                )
                if res.status_code == 200:
                    respuesta = res.json().get("response", "").strip()
                    # Si devuelve algo sensato, lo concatenamos a la query original para maximizar hits
                    if respuesta and len(respuesta) < 200:
                        logger.info(f"Query expandida (HyDE): {query} -> {respuesta}")
                        return f"{query} {respuesta}"
        except Exception as e:
            logger.warning(f"Error en expand_query (HyDE): {e}")
            
        return query

    @classmethod
    async def generate_smart_replies(cls, mensaje: str, respuesta_ia: str) -> list[str]:
        """
        Genera 3 sugerencias de continuación para el chat basadas en la respuesta actual.
        """
        settings = get_settings()
        if settings.ai_provider != "ollama":
            return []
            
        prompt = f"""Basado en la siguiente interacción en una escribanía, genera EXACTAMENTE 3 opciones muy breves (max 5 palabras cada una) de lo que el usuario podría responder o preguntar a continuación. 
Solo devuelve un JSON estricto con un array de strings.
Ejemplo de formato: ["¿Cuánto cuesta?", "Crear acta", "Ver requisitos"]
Usuario: {mensaje[-100:]}
Asistente: {respuesta_ia[-500:]}"""

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    f"{settings.ollama_base_url}/api/generate",
                    json={
                        "model": settings.llm_model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                        "options": {"temperature": 0.3, "num_ctx": 1024}
                    }
                )
                if res.status_code == 200:
                    raw_json = res.json().get("response", "").strip()
                    try:
                        sugerencias = json.loads(raw_json)
                        if isinstance(sugerencias, list) and len(sugerencias) > 0:
                            return [str(s)[:40] for s in sugerencias[:3]]
                    except:
                        pass
        except Exception as e:
            logger.warning(f"Error generando smart replies: {e}")
            
        return []
