from typing import List, Optional
import datetime
from pydantic import BaseModel

# ----------- EQUIPO SCHEMAS -----------

class EquipoMiembroBase(BaseModel):
    nombre: str
    rol: str
    email: Optional[str] = None

class EquipoMiembroCreate(EquipoMiembroBase):
    pass

class EquipoMiembroResponse(EquipoMiembroBase):
    id: int
    workspace_id: int

    class Config:
        from_attributes = True

# ----------- TRAMITE SCHEMAS -----------

class TramiteBase(BaseModel):
    nombre: str
    tipo: Optional[str] = None
    estado: str = "abierto"
    cliente_id: Optional[int] = None
    asignado_a_id: Optional[int] = None

class TramiteCreate(TramiteBase):
    pass

class TramiteResponse(TramiteBase):
    id: int
    workspace_id: int
    cliente_id: Optional[int] = None
    fecha_creacion: datetime.datetime
    fecha_actualizacion: datetime.datetime
    asignado_a: Optional[EquipoMiembroResponse] = None

    class Config:
        from_attributes = True

# ----------- OPERACIONES SCHEMAS -----------
class CatalogoOperacionBase(BaseModel):
    nombre: str
    jurisdiccion: str
    categoria: Optional[str] = None

class CatalogoOperacionResponse(CatalogoOperacionBase):
    id: int
    class Config:
        from_attributes = True

class TramiteOperacionBase(BaseModel):
    tramite_id: int
    catalogo_operacion_id: int

class TramiteOperacionResponse(TramiteOperacionBase):
    id: int
    operacion_catalogo: CatalogoOperacionResponse
    class Config:
        from_attributes = True

# ----------- CLIENTE SCHEMAS -----------

class ClienteBase(BaseModel):
    nombre_completo: str
    dni: str
    cuit: Optional[str] = None
    email: Optional[str] = None
    telefono: Optional[str] = None
    domicilio: Optional[str] = None
    tipo_persona: str = "Fisica"
    
    # Datos extendidos (Ingesis Parity)
    sexo: Optional[str] = None
    variante_nombre: Optional[str] = None
    variante_apellido: Optional[str] = None

    nacionalidad: Optional[str] = "Argentino"
    fecha_nacimiento: Optional[datetime.date] = None
    lugar_nacimiento: Optional[str] = None
    tipo_documento: Optional[str] = "DNI"
    emision_documento: Optional[datetime.date] = None
    tramite_nro_documento: Optional[str] = None
    ejemplar_documento: Optional[str] = None
    vencimiento_documento: Optional[datetime.date] = None

    exhibio_documento_idoneo: Optional[bool] = False
    tipo_documento_impositivo: Optional[str] = None
    condicion_iva: Optional[str] = None
    inscripto_ganancias: Optional[bool] = False

    emails_adicionales: Optional[str] = None
    telefonos_adicionales: Optional[str] = None
    pagina_web: Optional[str] = None

    domicilio_calle: Optional[str] = None
    domicilio_numero: Optional[str] = None
    domicilio_piso: Optional[str] = None
    domicilio_depto: Optional[str] = None
    domicilio_sector: Optional[str] = None
    domicilio_torre: Optional[str] = None
    domicilio_manzana: Optional[str] = None
    domicilio_barrio: Optional[str] = None
    domicilio_cp: Optional[str] = None
    domicilio_localidad: Optional[str] = None
    domicilio_partido_departamento: Optional[str] = None
    domicilio_provincia: Optional[str] = None
    domicilio_pais: Optional[str] = None
    domicilio_fiscal_diferente: Optional[bool] = False

    nombre_padre: Optional[str] = None
    apellido_padre: Optional[str] = None
    nombre_madre: Optional[str] = None
    apellido_madre: Optional[str] = None
    estado_familia: Optional[str] = None
    union_convivencial: Optional[bool] = False
    
    onboarding_token: Optional[str] = None

    # UIF / PEP
    es_pep: bool = False
    riesgo_uif: str = "Falta clasificación de riesgo"
    uif_observaciones: Optional[str] = None

class ClienteCreate(ClienteBase):
    pass

class ClienteResponse(ClienteBase):
    id: int
    workspace_id: int
    fecha_creacion: datetime.datetime

    class Config:
        from_attributes = True

# ----------- WORKSPACE SCHEMAS -----------

class WorkspaceBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    jurisdiccion: Optional[str] = None

class WorkspaceCreate(WorkspaceBase):
    pass

class WorkspaceResponse(WorkspaceBase):
    id: int
    fecha_creacion: datetime.datetime
    tramites: List[TramiteResponse] = []
    clientes: List[ClienteResponse] = []
    equipo: List[EquipoMiembroResponse] = []

    class Config:
        from_attributes = True

# --- Libro de Requerimientos ---
class LibroRequerimientoBase(BaseModel):
    tramite_id: Optional[int] = None
    nro_correlativo: int
    tipo_acto: str
    intervinientes: str
    fojas: Optional[str] = None

class LibroRequerimientoCreate(LibroRequerimientoBase):
    pass

class LibroRequerimientoResponse(LibroRequerimientoBase):
    id: int
    workspace_id: int
    fecha_asiento: datetime.datetime

    class Config:
        from_attributes = True

# --- Memoria Notarial ---
class MemoriaNotarialBase(BaseModel):
    preferencia: str
    categoria: Optional[str] = "general"

class MemoriaNotarialCreate(MemoriaNotarialBase):
    pass

class MemoriaNotarialResponse(MemoriaNotarialBase):
    id: int
    workspace_id: int
    fecha_creacion: datetime.datetime

    class Config:
        from_attributes = True

# --- Fojas Notariales ---
class ChequeFojasCreate(BaseModel):
    numero_desde: int
    numero_hasta: int
    descripcion: Optional[str] = None

class ChequeFojasResponse(ChequeFojasCreate):
    id: int
    workspace_id: int
    activo: bool
    fecha_compra: datetime.datetime
    total_fojas: int = 0
    fojas_usadas: int = 0
    fojas_disponibles: int = 0

    class Config:
        from_attributes = True

class FojaUsadaCreate(BaseModel):
    numero_foja: int
    chequera_id: int
    tipo_acto: str
    tramite_id: Optional[int] = None
    observaciones: Optional[str] = None

class FojaUsadaResponse(FojaUsadaCreate):
    id: int
    workspace_id: int
    fecha_uso: datetime.datetime

    class Config:
        from_attributes = True

class StockFojasResponse(BaseModel):
    total_fojas: int
    fojas_usadas: int
    fojas_disponibles: int
    alerta_stock_bajo: bool
    umbral_alerta: int = 50
    chequeras_activas: int
