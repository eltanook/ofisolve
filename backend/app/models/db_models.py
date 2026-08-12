from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Boolean, Enum, Numeric, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
import datetime
import enum
from typing import List, Optional
from decimal import Decimal

from app.core.database import Base

class UserRole(str, enum.Enum):
    ADMIN = "Admin"
    ESCRIBANO = "Escribano"
    EMPLEADO = "Empleado"

class TipoMovimiento(str, enum.Enum):
    INGRESO = "ingreso"
    EGRESO = "egreso"

class EstadoPresupuesto(str, enum.Enum):
    BORRADOR = "borrador"
    ENVIADO = "enviado"
    ACEPTADO = "aceptado"
    RECHAZADO = "rechazado"

class TipoEvento(str, enum.Enum):
    TURNO = "turno"
    VENCIMIENTO = "vencimiento"
    AUDIENCIA = "audiencia"
    RECORDATORIO = "recordatorio"

class VisibilidadNota(str, enum.Enum):
    PERSONAL = "personal"
    EQUIPO = "equipo"

class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    workspace_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workspaces.id"), nullable=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    nombre_completo: Mapped[str] = mapped_column(String(100))
    nro_matricula: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    escribania_nombre: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    rol: Mapped[UserRole] = mapped_column(String(20), default=UserRole.EMPLEADO)
    is_active: Mapped[bool] = mapped_column(default=True)
    is_superuser: Mapped[bool] = mapped_column(default=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.utcnow)

    workspace: Mapped[Optional["Workspace"]] = relationship()

class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String(100), index=True)
    descripcion: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    moneda_defecto: Mapped[Optional[str]] = mapped_column(String(10), default="ARS")
    iva_defecto: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), default=21.0)
    modelo_ia: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    jurisdiccion: Mapped[Optional[str]] = mapped_column(String(100), default="CABA")
    fecha_creacion: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.utcnow)
    
    tramites: Mapped[List["Tramite"]] = relationship(back_populates="workspace", cascade="all, delete")
    clientes: Mapped[List["Cliente"]] = relationship(back_populates="workspace", cascade="all, delete")
    equipo: Mapped[List["EquipoMiembro"]] = relationship(back_populates="workspace", cascade="all, delete")
    documentos: Mapped[List["DocumentoLibreria"]] = relationship(back_populates="workspace", cascade="all, delete")
    
    # --- Módulos ERP Competitivos ---
    proveedores: Mapped[List["Proveedor"]] = relationship(back_populates="workspace", cascade="all, delete")
    categorias_financieras: Mapped[List["CategoriaFinanciera"]] = relationship(back_populates="workspace", cascade="all, delete")
    movimientos_financieros: Mapped[List["MovimientoFinanciero"]] = relationship(back_populates="workspace", cascade="all, delete")
    presupuestos: Mapped[List["Presupuesto"]] = relationship(back_populates="workspace", cascade="all, delete")
    eventos_agenda: Mapped[List["EventoAgenda"]] = relationship(back_populates="workspace", cascade="all, delete")
    notas: Mapped[List["Nota"]] = relationship(back_populates="workspace", cascade="all, delete")
    plantillas: Mapped[List["PlantillaModelo"]] = relationship(back_populates="workspace", cascade="all, delete")
    configuracion_aranceles: Mapped[List["ConfiguracionAranceles"]] = relationship(back_populates="workspace", cascade="all, delete")

class DocumentoLibreria(Base):
    __tablename__ = "documentos_libreria"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"))
    cliente_id: Mapped[Optional[int]] = mapped_column(ForeignKey("clientes.id"), nullable=True)
    tramite_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tramites.id"), nullable=True)
    nombre: Mapped[str] = mapped_column(String(150))
    tipo: Mapped[str] = mapped_column(String(50)) # pdf, docx, etc.
    path: Mapped[str] = mapped_column(String(255))
    is_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    thread_id_langgraph: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    fecha_subida: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.utcnow)
    
    locked_by_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    locked_at: Mapped[Optional[datetime.datetime]] = mapped_column(nullable=True)

    workspace: Mapped["Workspace"] = relationship(back_populates="documentos")
    cliente: Mapped[Optional["Cliente"]] = relationship()
    tramite: Mapped[Optional["Tramite"]] = relationship(back_populates="documentos")
    mensajes_chat: Mapped[List["MensajeChat"]] = relationship(back_populates="documento", cascade="all, delete, delete-orphan")
    locked_by: Mapped[Optional["Usuario"]] = relationship()
    versiones: Mapped[List["DocumentoVersion"]] = relationship(back_populates="documento", cascade="all, delete, delete-orphan")

class DocumentoVersion(Base):
    """
    Control de versiones inmutable para documentos, permitiendo auditoría y comparación de cambios.
    """
    __tablename__ = "documento_versiones"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    documento_id: Mapped[int] = mapped_column(ForeignKey("documentos_libreria.id", ondelete="CASCADE"), index=True)
    autor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    comentario: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    path_archivo: Mapped[str] = mapped_column(String(255))
    timestamp: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.utcnow)

    documento: Mapped["DocumentoLibreria"] = relationship(back_populates="versiones")
    autor: Mapped[Optional["Usuario"]] = relationship()

class EquipoMiembro(Base):
    __tablename__ = "equipo_miembros"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"))
    nombre: Mapped[str] = mapped_column(String(100))
    rol: Mapped[str] = mapped_column(String(50))
    email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    workspace: Mapped["Workspace"] = relationship(back_populates="equipo")

class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"))
    nombre_completo: Mapped[str] = mapped_column(String(150), index=True)
    sexo: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    variante_nombre: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    variante_apellido: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    
    # --- Datos Personales Extendidos (Ingesis Parity) ---
    nacionalidad: Mapped[str] = mapped_column(String(50), default="Argentino")
    fecha_nacimiento: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)
    lugar_nacimiento: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    tipo_documento: Mapped[str] = mapped_column(String(50), default="DNI")
    dni: Mapped[str] = mapped_column(String(20), index=True)
    emision_documento: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)
    tramite_nro_documento: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    ejemplar_documento: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    vencimiento_documento: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)
    
    # --- Datos Impositivos y Justificación de Identidad ---
    exhibio_documento_idoneo: Mapped[bool] = mapped_column(Boolean, default=False)
    tipo_documento_impositivo: Mapped[Optional[str]] = mapped_column(String(20), nullable=True) # CUIT/CUIL
    cuit: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    condicion_iva: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    inscripto_ganancias: Mapped[bool] = mapped_column(Boolean, default=False)

    # --- Contactos Extendidos ---
    email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    emails_adicionales: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # JSON o CSV
    telefono: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    telefonos_adicionales: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # JSON o CSV
    pagina_web: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # --- Domicilios ---
    domicilio_calle: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    domicilio_numero: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    domicilio_piso: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    domicilio_depto: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    domicilio_sector: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    domicilio_torre: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    domicilio_manzana: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    domicilio_barrio: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    domicilio_cp: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    domicilio_localidad: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    domicilio_partido_departamento: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    domicilio_provincia: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    domicilio_pais: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    domicilio_fiscal_diferente: Mapped[bool] = mapped_column(Boolean, default=False)
    domicilio: Mapped[Optional[str]] = mapped_column(String(255), nullable=True) # Legacy

    # --- Filiación y Familia ---
    nombre_padre: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    apellido_padre: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    nombre_madre: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    apellido_madre: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    estado_familia: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    union_convivencial: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # --- Web Onboarding (Token) ---
    onboarding_token: Mapped[Optional[str]] = mapped_column(String(100), unique=True, index=True, nullable=True)

    tipo_persona: Mapped[str] = mapped_column(String(20), default="Fisica") # Fisica o Juridica
    
    # --- Módulo Cumplimiento Normativo (UIF / PEP) ---
    es_pep: Mapped[bool] = mapped_column(Boolean, default=False)
    riesgo_uif: Mapped[str] = mapped_column(String(50), default="Falta clasificación de riesgo") 
    uif_observaciones: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    uif_estado: Mapped[str] = mapped_column(String(50), default="Aprobado")
    uif_ultima_revision: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)

    fecha_creacion: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.utcnow)

    workspace: Mapped["Workspace"] = relationship(back_populates="clientes")
    participaciones: Mapped[List["Participacion"]] = relationship(back_populates="cliente", cascade="all, delete, delete-orphan")
    mensajes_chat: Mapped[List["MensajeChat"]] = relationship(back_populates="cliente", cascade="all, delete, delete-orphan")

class CatalogoOperacion(Base):
    """
    Catálogo de Operaciones Notariales por Jurisdicción (Ingesis Parity).
    """
    __tablename__ = "catalogo_operaciones"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String(200), index=True)
    jurisdiccion: Mapped[str] = mapped_column(String(100), index=True)
    categoria: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Relacion Inversa
    tramites_vinculados: Mapped[List["TramiteOperacion"]] = relationship(back_populates="operacion_catalogo", cascade="all, delete-orphan")


class Tramite(Base):
    __tablename__ = "tramites"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"))
    cliente_id: Mapped[Optional[int]] = mapped_column(ForeignKey("clientes.id"), nullable=True)
    asignado_a_id: Mapped[Optional[int]] = mapped_column(ForeignKey("equipo_miembros.id"), nullable=True)
    nombre: Mapped[str] = mapped_column(String(100), index=True) # Nombre de Carpeta
    tipo: Mapped[Optional[str]] = mapped_column(String(50), nullable=True) # Legacy (se reemplazara por Operaciones)
    estado: Mapped[str] = mapped_column(String(50), default="abierto")
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_extra: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fecha_creacion: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.utcnow)
    fecha_actualizacion: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    workspace: Mapped["Workspace"] = relationship(back_populates="tramites")
    cliente: Mapped[Optional["Cliente"]] = relationship()
    asignado_a: Mapped[Optional["EquipoMiembro"]] = relationship()
    participaciones: Mapped[List["Participacion"]] = relationship(back_populates="tramite", cascade="all, delete, delete-orphan")
    documentos: Mapped[List["DocumentoLibreria"]] = relationship(back_populates="tramite", cascade="all, delete, delete-orphan")
    mensajes_chat: Mapped[List["MensajeChat"]] = relationship(back_populates="tramite", cascade="all, delete, delete-orphan")
    
    operaciones: Mapped[List["TramiteOperacion"]] = relationship(back_populates="tramite", cascade="all, delete-orphan")

class TramiteOperacion(Base):
    """
    Operaciones que contiene una Carpeta(Tramite).
    """
    __tablename__ = "tramite_operaciones"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tramite_id: Mapped[int] = mapped_column(ForeignKey("tramites.id"), index=True)
    catalogo_operacion_id: Mapped[int] = mapped_column(ForeignKey("catalogo_operaciones.id"), index=True)

    tramite: Mapped["Tramite"] = relationship(back_populates="operaciones")
    operacion_catalogo: Mapped["CatalogoOperacion"] = relationship(back_populates="tramites_vinculados")


class Participacion(Base):
    __tablename__ = "participaciones"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"))
    tramite_id: Mapped[int] = mapped_column(ForeignKey("tramites.id"))
    rol: Mapped[str] = mapped_column(String(100)) # Ej: Comprador, Vendedor, Requirente

    cliente: Mapped["Cliente"] = relationship(back_populates="participaciones")
    tramite: Mapped["Tramite"] = relationship(back_populates="participaciones")


class ChatSession(Base):
    """
    Persiste sesiones de chat independientes, ej. Gestor Global de Clientes.
    """
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    titulo: Mapped[str] = mapped_column(String(255))
    tipo: Mapped[str] = mapped_column(String(50), default="global") # global, tramite, etc
    fecha_creacion: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.utcnow)

    workspace: Mapped["Workspace"] = relationship()
    mensajes: Mapped[List["MensajeChat"]] = relationship(back_populates="chat_session", cascade="all, delete-orphan")

class MensajeChat(Base):
    """
    Persiste el historial de chat por documento (Mejora: Chat Permanente por Archivo).
    """
    __tablename__ = "mensajes_chat"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    cliente_id: Mapped[Optional[int]] = mapped_column(ForeignKey("clientes.id"), index=True, nullable=True)
    documento_id: Mapped[Optional[int]] = mapped_column(ForeignKey("documentos_libreria.id"), index=True, nullable=True)
    tramite_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tramites.id"), index=True, nullable=True)
    chat_session_id: Mapped[Optional[int]] = mapped_column(ForeignKey("chat_sessions.id"), index=True, nullable=True)
    role: Mapped[str] = mapped_column(String(20)) # "user" o "assistant"
    modo: Mapped[str] = mapped_column(String(20), default="creador", server_default="creador") # "consultas" o "creador"
    contenido: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.utcnow)

    cliente: Mapped[Optional["Cliente"]] = relationship(back_populates="mensajes_chat")
    documento: Mapped[Optional["DocumentoLibreria"]] = relationship(back_populates="mensajes_chat")
    tramite: Mapped[Optional["Tramite"]] = relationship(back_populates="mensajes_chat")
    chat_session: Mapped[Optional["ChatSession"]] = relationship(back_populates="mensajes")

class MemoriaNotarial(Base):
    """
    Persiste preferencias, reglas y datos de contexto aprendidos del usuario a largo plazo.
    """
    __tablename__ = "memoria_notarial"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    preferencia: Mapped[str] = mapped_column(Text)
    categoria: Mapped[str] = mapped_column(String(50), default="general") # "formato", "estilo", "dato"
    fecha_creacion: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.utcnow)
    
    workspace: Mapped["Workspace"] = relationship()

class AuditLog(Base):
    """
    Trazabilidad Legal Inmutable de la Escribanía.
    """
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    accion: Mapped[str] = mapped_column(String(255)) # Ej: DELETE_TRAMITE, SIGN_DOCUMENT
    entidad: Mapped[str] = mapped_column(String(100)) # Ej: tramite, documento
    entidad_id: Mapped[int] = mapped_column(Integer)
    detalles: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.utcnow)

    usuario: Mapped["Usuario"] = relationship()

class LibroRequerimiento(Base):
    """
    Asiento automático de certificaciones y actuaciones en el Libro de Requerimientos.
    """
    __tablename__ = "libro_requerimientos"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    tramite_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tramites.id"), nullable=True)
    fecha_asiento: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.utcnow, index=True)
    nro_correlativo: Mapped[int] = mapped_column(Integer, index=True)
    tipo_acto: Mapped[str] = mapped_column(String(100))
    intervinientes: Mapped[str] = mapped_column(Text)
    fojas: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    workspace: Mapped["Workspace"] = relationship()
    tramite: Mapped[Optional["Tramite"]] = relationship()

class ChequeFojas(Base):
    """
    Chequera de fojas notariales comprada al Colegio de Escribanos.
    Contiene un rango de números de foja (desde / hasta).
    """
    __tablename__ = "cheques_fojas"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    numero_desde: Mapped[int] = mapped_column(Integer, index=True)
    numero_hasta: Mapped[int] = mapped_column(Integer)
    descripcion: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    fecha_compra: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.utcnow)

    workspace: Mapped["Workspace"] = relationship()
    fojas_usadas: Mapped[List["FojaUsada"]] = relationship(back_populates="chequera", cascade="all, delete")

class FojaUsada(Base):
    """
    Registro de cada foja individual consumida en un acto notarial.
    """
    __tablename__ = "fojas_usadas"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    chequera_id: Mapped[int] = mapped_column(ForeignKey("cheques_fojas.id"))
    numero_foja: Mapped[int] = mapped_column(Integer, index=True)
    tramite_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tramites.id"), nullable=True)
    tipo_acto: Mapped[str] = mapped_column(String(150))
    observaciones: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    fecha_uso: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.utcnow, index=True)

    workspace: Mapped["Workspace"] = relationship()
    chequera: Mapped["ChequeFojas"] = relationship(back_populates="fojas_usadas")
    tramite: Mapped[Optional["Tramite"]] = relationship()


# ==============================================================================
# MÓDULOS ERP COMPETITIVOS (Paridad con iNOTARY + Superioridad Local)
# ==============================================================================

class Proveedor(Base):
    """
    Directorio de proveedores, gestores, peritos y colegas de la escribanía.
    Equivalente al módulo "Clientes y Proveedores" de iNOTARY.
    """
    __tablename__ = "proveedores"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    nombre_completo: Mapped[str] = mapped_column(String(200), index=True)
    cuit: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    telefono: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    domicilio: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tipo: Mapped[str] = mapped_column(String(50), default="Gestor")  # Gestor, Perito, Colega, Registro, Otro
    notas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    fecha_creacion: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.utcnow)

    workspace: Mapped["Workspace"] = relationship(back_populates="proveedores")
    movimientos: Mapped[List["MovimientoFinanciero"]] = relationship(back_populates="proveedor")


class CategoriaFinanciera(Base):
    """
    Categorías para clasificar movimientos financieros.
    Ej: Honorarios, Sellos, Aportes Caja Notarial, Gastos Operativos.
    """
    __tablename__ = "categorias_financieras"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    nombre: Mapped[str] = mapped_column(String(100))
    tipo_default: Mapped[str] = mapped_column(String(10), default="egreso")  # ingreso | egreso
    color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)  # Hex color para UI
    icono: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)  # Nombre de icono Lucide
    es_sistema: Mapped[bool] = mapped_column(Boolean, default=False)  # True = no eliminable

    workspace: Mapped["Workspace"] = relationship(back_populates="categorias_financieras")
    movimientos: Mapped[List["MovimientoFinanciero"]] = relationship(back_populates="categoria")


class MovimientoFinanciero(Base):
    """
    Registro de cada ingreso o egreso de la escribanía.
    Equivalente al módulo "Finanzas" + "Flujo de Caja" de iNOTARY.
    Usa Numeric(12,2) para evitar errores de punto flotante en montos.
    """
    __tablename__ = "movimientos_financieros"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    tipo: Mapped[str] = mapped_column(String(10), index=True)  # ingreso | egreso
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    descripcion: Mapped[str] = mapped_column(String(255))
    fecha: Mapped[datetime.date] = mapped_column(Date, index=True)
    
    # Relaciones opcionales para trazabilidad
    categoria_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categorias_financieras.id"), nullable=True)
    cliente_id: Mapped[Optional[int]] = mapped_column(ForeignKey("clientes.id"), nullable=True)
    proveedor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("proveedores.id"), nullable=True)
    tramite_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tramites.id"), nullable=True)
    
    comprobante_tipo: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # Factura A, B, C, Recibo, Otro
    comprobante_nro: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    estado: Mapped[str] = mapped_column(String(20), default="confirmado")  # confirmado | pendiente | anulado
    fecha_creacion: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.utcnow)

    workspace: Mapped["Workspace"] = relationship(back_populates="movimientos_financieros")
    categoria: Mapped[Optional["CategoriaFinanciera"]] = relationship(back_populates="movimientos")
    cliente: Mapped[Optional["Cliente"]] = relationship()
    proveedor: Mapped[Optional["Proveedor"]] = relationship(back_populates="movimientos")
    tramite: Mapped[Optional["Tramite"]] = relationship()


class Presupuesto(Base):
    """
    Presupuesto generado para un cliente.
    Equivalente al módulo "Presupuestador y Rentas" de iNOTARY.
    """
    __tablename__ = "presupuestos"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    cliente_id: Mapped[Optional[int]] = mapped_column(ForeignKey("clientes.id"), nullable=True)
    tramite_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tramites.id"), nullable=True)
    
    titulo: Mapped[str] = mapped_column(String(200))
    tipo_acto: Mapped[str] = mapped_column(String(100))  # Compraventa, Donación, Hipoteca, etc.
    monto_operacion: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    estado: Mapped[str] = mapped_column(String(20), default="borrador")  # borrador | enviado | aceptado | rechazado
    observaciones: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    fecha_creacion: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.utcnow)
    fecha_envio: Mapped[Optional[datetime.datetime]] = mapped_column(nullable=True)
    fecha_vencimiento: Mapped[Optional[datetime.date]] = mapped_column(nullable=True)

    workspace: Mapped["Workspace"] = relationship(back_populates="presupuestos")
    cliente: Mapped[Optional["Cliente"]] = relationship()
    tramite: Mapped[Optional["Tramite"]] = relationship()
    items: Mapped[List["PresupuestoItem"]] = relationship(back_populates="presupuesto", cascade="all, delete-orphan")

    @property
    def total(self) -> Decimal:
        return sum(item.monto for item in self.items) if self.items else Decimal("0.00")


class PresupuestoItem(Base):
    """
    Línea individual de un presupuesto (honorarios, sellos, aportes, etc.).
    """
    __tablename__ = "presupuesto_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    presupuesto_id: Mapped[int] = mapped_column(ForeignKey("presupuestos.id"), index=True)
    concepto: Mapped[str] = mapped_column(String(200))
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    es_porcentaje: Mapped[bool] = mapped_column(Boolean, default=False)  # Si True, monto es un % del monto_operacion
    porcentaje_valor: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4), nullable=True)  # Ej: 0.0200 = 2%
    orden: Mapped[int] = mapped_column(Integer, default=0)  # Para mantener el orden de display

    presupuesto: Mapped["Presupuesto"] = relationship(back_populates="items")


class EventoAgenda(Base):
    """
    Eventos de agenda: turnos, audiencias, vencimientos de certificados.
    Equivalente al módulo "Agenda" de iNOTARY.
    """
    __tablename__ = "eventos_agenda"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    titulo: Mapped[str] = mapped_column(String(200))
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tipo: Mapped[str] = mapped_column(String(20), default="turno")  # turno | vencimiento | audiencia | recordatorio
    
    fecha_inicio: Mapped[datetime.datetime] = mapped_column(DateTime, index=True)
    fecha_fin: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    todo_el_dia: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Relaciones opcionales
    cliente_id: Mapped[Optional[int]] = mapped_column(ForeignKey("clientes.id"), nullable=True)
    tramite_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tramites.id"), nullable=True)
    asignado_a_id: Mapped[Optional[int]] = mapped_column(ForeignKey("equipo_miembros.id"), nullable=True)
    
    color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)  # Hex color
    completado: Mapped[bool] = mapped_column(Boolean, default=False)
    recordatorio_enviado: Mapped[bool] = mapped_column(Boolean, default=False)
    fecha_creacion: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.utcnow)

    workspace: Mapped["Workspace"] = relationship(back_populates="eventos_agenda")
    cliente: Mapped[Optional["Cliente"]] = relationship()
    tramite: Mapped[Optional["Tramite"]] = relationship()
    asignado_a: Mapped[Optional["EquipoMiembro"]] = relationship()


class Nota(Base):
    """
    Notas personales o colaborativas, tipo Post-it virtual.
    Equivalente al módulo "Notas" de iNOTARY.
    """
    __tablename__ = "notas"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    autor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("equipo_miembros.id"), nullable=True)
    
    titulo: Mapped[str] = mapped_column(String(200))
    contenido: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    color: Mapped[str] = mapped_column(String(7), default="#FEF3C7")  # Amarillo pastel por defecto
    visibilidad: Mapped[str] = mapped_column(String(10), default="equipo")  # personal | equipo
    fijada: Mapped[bool] = mapped_column(Boolean, default=False)  # Pin to top
    fecha_creacion: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.utcnow)
    fecha_actualizacion: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    workspace: Mapped["Workspace"] = relationship(back_populates="notas")
    autor: Mapped[Optional["EquipoMiembro"]] = relationship()


class ConfiguracionAranceles(Base):
    """
    Tabla de aranceles del Colegio de Escribanos, actualizable por el usuario.
    Permite calcular presupuestos automáticamente.
    """
    __tablename__ = "configuracion_aranceles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    concepto: Mapped[str] = mapped_column(String(150))  # Ej: "Honorarios Escritura", "Sello Provincial"
    tipo_calculo: Mapped[str] = mapped_column(String(20))  # porcentaje | fijo
    valor: Mapped[Decimal] = mapped_column(Numeric(10, 4))  # 0.0200 = 2% o monto fijo
    minimo: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)  # Honorario mínimo
    aplica_a: Mapped[str] = mapped_column(String(100), default="todos")  # todos | compraventa | hipoteca | donacion
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    orden: Mapped[int] = mapped_column(Integer, default=0)
    fecha_actualizacion: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.utcnow)

    workspace: Mapped["Workspace"] = relationship(back_populates="configuracion_aranceles")


class PlantillaModelo(Base):
    """
    Biblioteca de modelos/plantillas reutilizables para documentos notariales.
    Equivalente al módulo "Biblioteca" de iNOTARY.
    """
    __tablename__ = "plantillas_modelos"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    nombre: Mapped[str] = mapped_column(String(200), index=True)
    categoria: Mapped[str] = mapped_column(String(50))  # escritura | certificacion | poder | acta | otro
    contenido: Mapped[str] = mapped_column(Text)  # Contenido del modelo/template
    descripcion: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    es_favorito: Mapped[bool] = mapped_column(Boolean, default=False)
    uso_count: Mapped[int] = mapped_column(Integer, default=0)  # Contador de usos
    fecha_creacion: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.utcnow)
    fecha_actualizacion: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    workspace: Mapped["Workspace"] = relationship(back_populates="plantillas")
