import difflib
import os
from typing import List, Dict, Any
from loguru import logger
from app.rag.rag_service import _extract_text

class DiffService:
    """
    Servicio para comparar dos versiones de un documento y resaltar las diferencias,
    similar a un diff de control de versiones.
    """
    @staticmethod
    def compare_documents(path_v1: str, path_v2: str) -> Dict[str, Any]:
        """
        Compara dos documentos dado sus rutas locales y devuelve un diff detallado.
        """
        if not os.path.exists(path_v1):
            return {"error": f"Archivo no encontrado: {path_v1}"}
        if not os.path.exists(path_v2):
            return {"error": f"Archivo no encontrado: {path_v2}"}
        
        try:
            # Extraer texto de ambas versiones
            text_v1 = _extract_text(path_v1, None, os.path.basename(path_v1))
            text_v2 = _extract_text(path_v2, None, os.path.basename(path_v2))
            
            # Limpiar lineas
            lines_v1 = [line for line in text_v1.splitlines() if line.strip()]
            lines_v2 = [line for line in text_v2.splitlines() if line.strip()]

            # Usar ndiff para obtener un output legible y estructurado
            differ = difflib.ndiff(lines_v1, lines_v2)
            diff_output = list(differ)

            # Clasificar los cambios para facilitar el frontend
            changes = []
            agregados = 0
            removidos = 0

            for line in diff_output:
                if line.startswith('  '):
                    continue # Sin cambios
                elif line.startswith('- '):
                    changes.append({"tipo": "removed", "texto": line[2:]})
                    removidos += 1
                elif line.startswith('+ '):
                    changes.append({"tipo": "added", "texto": line[2:]})
                    agregados += 1
                elif line.startswith('? '):
                    pass # Indicador intralínea, lo omitimos para mantenerlo simple

            logger.info(f"Diff completado: {agregados} agregados, {removidos} removidos.")
            return {
                "success": True,
                "changes": changes,
                "stats": {
                    "added": agregados,
                    "removed": removidos
                }
            }
        except Exception as e:
            logger.error(f"Error al comparar documentos: {str(e)}")
            return {"error": str(e)}

diff_service = DiffService()
