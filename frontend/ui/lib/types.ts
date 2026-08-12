/**
 * =============================================================================
 * OFISOLVE - TIPOS TYPESCRIPT DEL BACKEND
 * =============================================================================
 * 
 * Este archivo contiene todas las interfaces TypeScript que mapean
 * exactamente las estructuras de datos del backend FastAPI.
 * 
 * BASE URL: http://localhost:8000
 * 
 * @author OfiSolve Team
 * @version 1.0.0
 */

// =============================================================================
// TIPOS DE CERTIFICACION - POST /api/v1/generate/certificacion
// =============================================================================

/**
 * Tipos de documento que se pueden certificar
 * Corresponde al enum del backend
 */
export type TipoDocumentoACertificar = 
  | "fotocopia" 
  | "firma" 
  | "contenido" 
  | "fecha_cierta"
  | "viaje_menores"
  | "supervivencia"

export interface EquipoMiembroBase {
  nombre: string
  rol: string
  email?: string
}

export interface EquipoMiembroCreate extends EquipoMiembroBase {}

export interface EquipoMiembroResponse extends EquipoMiembroBase {
  id: number
  workspace_id: number
}

export interface ClienteBase {
  nombre_completo: string
  dni: string
  cuit?: string
  email?: string
  telefono?: string
  domicilio?: string
  tipo_persona: string
}

export interface ClienteCreate extends ClienteBase {}

export interface ClienteResponse extends ClienteBase {
  id: number
  workspace_id: number
  fecha_creacion: string
}

export interface WorkspaceBase {
  nombre: string
  descripcion?: string
  jurisdiccion?: string
}

export interface WorkspaceCreate extends WorkspaceBase {}

export interface WorkspaceResponse extends WorkspaceBase {
  id: number
  fecha_creacion: string
  tramites: TramiteResponse[]
  clientes: ClienteResponse[]
  equipo: EquipoMiembroResponse[]
}

export interface TramiteBase {
  nombre: string
  tipo: string
  estado?: string
  asignado_a_id?: number
}

export interface TramiteCreate extends TramiteBase {}

export interface TramiteResponse extends TramiteBase {
  id: number
  workspace_id: number
  fecha_creacion: string
  fecha_actualizacion: string
  asignado_a?: EquipoMiembroResponse
}

export interface ChatNotarialRequest {
  query: string
  history?: Array<{ role: 'user' | 'assistant'; content: string }>
  fuentes_seleccionadas?: string[]
}

export interface ChatNotarialResponse {
  respuesta: string
  fuentes_utilizadas: string[]
}

/**
 * Request body para generar una certificacion
 * Endpoint: POST /api/v1/generate/certificacion
 */
export interface CertificacionRequest {
  /** Nombre completo del requirente - Min 2, max 200 chars */
  nombre_requirente: string
  
  /** DNI sin puntos - 7-8 digitos, regex: /^\d{7,8}$/ */
  dni: string
  
  /** Tipo de documento a certificar */
  tipo_documento_a_certificar: TipoDocumentoACertificar
  
  /** Domicilio del requirente - Max 500 chars (opcional) */
  domicilio?: string
  
  /** CUIT formato XX-XXXXXXXX-X, regex: /^\d{2}-\d{8}-\d{1}$/ (opcional) */
  cuit?: string
  
  /** Observaciones adicionales - Max 1000 chars (opcional) */
  observaciones?: string

  /** Fuentes normativas RAG a utilizar (opcional) */
  fuentes_seleccionadas?: string[]
}

/**
 * Representación de un documento base de conocimiento RAG (ChromaDB)
 */
export interface FuenteRag {
  id: string
  titulo: string
  fuente: string
  tipo: string
  jurisdiccion: string
}

/**
 * Query parameters para el endpoint de certificacion
 */
export interface CertificacionQueryParams {
  /** Formato de respuesta: json (default) o docx (descarga directa) */
  format?: "json" | "docx"
  
  /** Nombre del escribano para el documento */
  nombre_escribano?: string
  
  /** Numero de registro notarial */
  nro_registro?: string
}

/**
 * Estado del documento generado
 */
export type EstadoDocumento = 
  | "borrador" 
  | "pendiente_revision" 
  | "aprobado" 
  | "firmado" 
  | "anulado"

/**
 * Modo del LLM utilizado para la generacion
 */
export type ModoLLM = "mock" | "ollama"

/**
 * Informacion de anonimizacion de datos sensibles
 */
export interface InfoAnonimizacion {
  /** Cantidad de campos que fueron anonimizados */
  campos_anonimizados: number
  
  /** Tipos de datos sensibles detectados - Ej: ["NOMBRE", "DNI", "CUIT", "DOMICILIO"] */
  tipos_detectados: string[]
}

export interface PersonaExtraidaResponse {
  nombre: string
  dni_cuit: string
  rol: string
}

export interface DatosExtraidosResponse {
  tramite_id: number
  tipo_acto: string
  clientes: PersonaExtraidaResponse[]
}

/**
 * Response del endpoint de certificacion (format=json)
 * Endpoint: POST /api/v1/generate/certificacion
 */
export interface CertificacionResponse {
  /** UUID del documento generado */
  id: string
  
  /** Texto final de la certificacion */
  texto_generado: string
  
  /** Estado actual del documento */
  estado: EstadoDocumento
  
  /** Informacion de anonimizacion */
  anonimizacion: InfoAnonimizacion
  
  /** Siempre true - Human-in-the-Loop */
  requiere_revision: boolean
  
  /** Nombre del archivo DOCX generado (si aplica) */
  archivo_docx: string | null
  
  /** Ruta para descargar el archivo - Ej: "/api/v1/generate/descargar/cert_xxx.docx" */
  ruta_descarga: string | null
  
  /** Modo del LLM utilizado */
  modo_llm: ModoLLM
  
  /** Fecha y hora de generacion - ISO datetime */
  generado_en: string

  /** Datos extraidos por el agente (NUEVO) */
  datos_extraidos?: DatosExtraidosResponse
}

// =============================================================================
// TIPOS DE RAG - POST /api/v1/generate/rag/ingestar
// =============================================================================

/**
 * Response de las estadisticas del RAG
 * Endpoint: GET /api/v1/generate/rag/stats
 */
export interface RAGStats {
  /** Total de documentos ingestados */
  total_documentos: number
  
  /** Total de chunks en el vector store */
  total_chunks: number
  
  /** Fecha de ultima ingesta */
  ultima_ingesta: string | null
  
  /** Estado del servicio RAG */
  estado: "activo" | "inactivo" | "error"
}

// =============================================================================
// TIPOS DE HEALTH CHECK
// =============================================================================

/**
 * Response del health check
 * Endpoints: GET /health, GET /api/v1/generate/health
 */
export interface HealthResponse {
  status: "healthy" | "unhealthy"
  timestamp: string
  version?: string
  services?: {
    database?: "ok" | "error"
    llm?: "ok" | "error"
    rag?: "ok" | "error"
  }
}

// =============================================================================
// TIPOS DE ERROR
// =============================================================================

/**
 * Estructura de error del backend
 * Se retorna con status 422, 500, 503, etc.
 */
export interface ErrorResponse {
  /** Mensaje descriptivo del error */
  detail: string
  
  /** Codigo de error interno (opcional) */
  error_code?: string
  
  /** Timestamp del error (opcional) */
  timestamp?: string
}

/**
 * Error de validacion de FastAPI (status 422)
 */
export interface ValidationError {
  detail: Array<{
    loc: (string | number)[]
    msg: string
    type: string
  }>
}

// =============================================================================
// TIPOS DE USUARIO Y AUTENTICACION
// =============================================================================

export interface UserCreate {
  email: string
  password: string
  nombre_completo?: string
}

export interface UserResponse {
  id: number
  email: string
  nombre_completo?: string
  is_active: boolean
  tenant_id: string
}

export interface Token {
  access_token: string
  token_type: string
}

// =============================================================================
// TIPOS PARA LA UI - Extendidos para el frontend
// =============================================================================

/**
 * Usuario autenticado en el sistema
 * TODO: Integrar con sistema de auth cuando este disponible
 */
export interface Usuario {
  id: string
  tenant_id: string // UUID del tenant SaaS
  nombre: string
  nombre_completo?: string
  email: string
  avatar?: string
  rol: "escribano" | "asistente" | "admin"
  escribaniaId?: string
  escribaniaNombre?: string
  telefono?: string
  nroMatricula?: string
}

/**
 * Workspace (espacio de trabajo)
 */
export interface Workspace {
  id: number
  tenant_id: string // UUID asociado
  nombre: string
  descripcion?: string
  color?: string
  tramitesCount: number
  ultimaActividad: Date
}

/**
 * Tramite notarial
 */
export interface Tramite {
  id: number
  tenant_id: string // UUID asociado
  nombre: string
  estado: "borrador" | "en_progreso" | "completado" | "archivado"
  tipo: string
  workspaceId: number
  clienteId?: number
  fechaCreacion: Date
  fechaActualizacion: Date
}


/**
 * Documento fuente (adjunto al tramite)
 */
export interface DocumentoFuente {
  id: number
  nombre: string
  tipo: "pdf" | "word" | "link" | "image" | "excel"
  url?: string
  tamano?: number
  fechaSubida: Date
  seleccionado: boolean
}

/**
 * Mensaje en el chat
 */
export interface MensajeChat {
  id: number
  tipo: "usuario" | "ia"
  contenido: string
  referencias?: ReferenciaLegal[]
  timestamp: Date
}

/**
 * Referencia legal citada por la IA
 */
export interface ReferenciaLegal {
  id: number
  texto: string
  url?: string
}

/**
 * Alerta de auditoria legal
 */
export interface AlertaLegal {
  id: number
  tipo: "warning" | "success" | "info" | "error"
  titulo: string
  descripcion: string
  accion?: {
    label: string
    onClick: () => void
  }
}

/**
 * Tipo de documento generable por la IA
 */
export interface TipoDocumentoGenerable {
  id: string
  nombre: string
  descripcion: string
  categoria: "certificacion" | "poder" | "acta" | "escritura"
  icono: "stamp" | "signature" | "scroll" | "scale" | "gavel"
}

/**
 * Documento generado por la IA
 */
export interface DocumentoGenerado {
  id: number
  nombre: string
  tipo: string
  fechaGeneracion: Date
  version: number
  url?: string
  contenidoPreview?: string
  contenido?: string
  certificacionId?: string // UUID del backend si aplica
}

/**
 * Configuracion del usuario
 */
export interface ConfiguracionUsuario {
  tema: "light" | "dark" | "system"
  idioma: "es" | "en"
  notificaciones: boolean
  autoguardado: boolean
  formatoFecha: "dd/mm/yyyy" | "mm/dd/yyyy" | "yyyy-mm-dd"
}

/**
 * Cliente de la escribanía
 */
export interface Cliente {
  id: number
  nombre: string
  dni: string
  cuit: string
  domicilio: string
  estado_civil: string
  profesion: string
  email: string
  telefono: string
}

// =============================================================================
// TIPOS MÓDULOS ERP COMPETITIVOS
// =============================================================================

export interface Proveedor {
  id: number
  workspace_id: number
  nombre_completo: string
  cuit?: string
  email?: string
  telefono?: string
  domicilio?: string
  tipo: string
  notas?: string
  activo: boolean
  fecha_creacion: string
}

export interface CategoriaFinanciera {
  id: number
  workspace_id: number
  nombre: string
  tipo_default: string
  color?: string
  icono?: string
  es_sistema: boolean
}

export interface MovimientoFinanciero {
  id: number
  workspace_id: number
  tipo: "ingreso" | "egreso"
  monto: number
  descripcion: string
  fecha: string
  categoria_id?: number
  cliente_id?: number
  proveedor_id?: number
  tramite_id?: number
  comprobante_tipo?: string
  comprobante_nro?: string
  estado: string
  fecha_creacion: string
  categoria_nombre?: string
  cliente_nombre?: string
  proveedor_nombre?: string
}

export interface ResumenFinanciero {
  total_ingresos: number
  total_egresos: number
  saldo_neto: number
  pendiente_cobro: number
  cantidad_movimientos: number
  periodo: string
}

export interface FlujoCajaMensual {
  mes: string
  ingresos: number
  egresos: number
  saldo: number
}

export interface PresupuestoItem {
  id?: number
  presupuesto_id?: number
  concepto: string
  monto: number
  es_porcentaje: boolean
  porcentaje_valor?: number
  orden: number
}

export interface PresupuestoResponse {
  id: number
  workspace_id: number
  titulo: string
  tipo_acto: string
  monto_operacion: number
  estado: string
  cliente_id?: number
  tramite_id?: number
  observaciones?: string
  fecha_vencimiento?: string
  total: number
  fecha_creacion: string
  fecha_envio?: string
  items: PresupuestoItem[]
  cliente_nombre?: string
}

export interface EventoAgenda {
  id: number
  workspace_id: number
  titulo: string
  descripcion?: string
  tipo: "turno" | "vencimiento" | "audiencia" | "recordatorio"
  fecha_inicio: string
  fecha_fin?: string
  todo_el_dia: boolean
  cliente_id?: number
  tramite_id?: number
  asignado_a_id?: number
  color?: string
  completado: boolean
  recordatorio_enviado: boolean
  fecha_creacion: string
  cliente_nombre?: string
  asignado_a_nombre?: string
}

export interface NotaResponse {
  id: number
  workspace_id: number
  titulo: string
  contenido?: string
  color: string
  visibilidad: "personal" | "equipo"
  fijada: boolean
  autor_id?: number
  autor_nombre?: string
  fecha_creacion: string
  fecha_actualizacion: string
}

export interface ConfiguracionAranceles {
  id: number
  workspace_id: number
  concepto: string
  tipo_calculo: "porcentaje" | "fijo"
  valor: number
  minimo?: number
  aplica_a: string
  activo: boolean
  orden: number
  fecha_actualizacion: string
}

export interface CalculoArancelResponse {
  tipo_acto: string
  monto_operacion: number
  items: PresupuestoItem[]
  total: number
}

export interface PlantillaModelo {
  id: number
  workspace_id: number
  nombre: string
  categoria: string
  contenido: string
  descripcion?: string
  es_favorito: boolean
  uso_count: number
  fecha_creacion: string
  fecha_actualizacion: string
}
