from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class DocumentoLibreriaBase(BaseModel):
    nombre: str
    tipo: str
    path: Optional[str] = None

class DocumentoLibreriaCreate(DocumentoLibreriaBase):
    pass

class DocumentoLibreriaResponse(DocumentoLibreriaBase):
    id: int
    workspace_id: int
    fecha_subida: datetime

    class Config:
        from_attributes = True

class DocumentoVersionBase(BaseModel):
    version: int
    comentario: Optional[str] = None
    path_archivo: str

class DocumentoVersionCreate(DocumentoVersionBase):
    pass

class DocumentoVersionResponse(DocumentoVersionBase):
    id: int
    documento_id: int
    autor_id: Optional[int] = None
    timestamp: datetime

    class Config:
        from_attributes = True
