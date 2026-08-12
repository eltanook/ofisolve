"use client"
import Link from "next/link"
import { useQuery } from "@tanstack/react-query"
/**
 * =============================================================================
 * OFISOLVE - Sistema de IA para Escribanias Argentinas
 * =============================================================================
 * 
 * Este componente es la interfaz principal del asistente de IA para escribanias.
 * Implementa un layout de tres paneles redimensionables (sidebar, chat, auditoria)
 * inspirado en Google NotebookLM, adaptado para el flujo de trabajo notarial.
 * 
 * ARQUITECTURA:
 * - Panel Izquierdo: Gestion de fuentes documentales, workspaces y configuracion
 * - Area Central: Chat conversacional con el asistente de IA
 * - Panel Derecho: Generacion de documentos y auditoria legal
 * 
 * INTEGRACION CON BACKEND:
 * Este componente esta preparado para conectarse con un backend que provea:
 * 
 * API DE AUTENTICACION:
 * - GET  /api/auth/me              - Obtener usuario actual
 * - POST /api/auth/login           - Iniciar sesion
 * - POST /api/auth/logout          - Cerrar sesion
 * - PUT  /api/auth/profile         - Actualizar perfil
 * - PUT  /api/auth/password        - Cambiar contrasena
 * 
 * API DE WORKSPACES:
 * - GET  /api/workspaces           - Listar workspaces del usuario
 * - POST /api/workspaces           - Crear nuevo workspace
 * - PUT  /api/workspaces/:id       - Actualizar workspace
 * - DELETE /api/workspaces/:id     - Eliminar workspace
 * 
 * API DE TRAMITES:
 * - GET  /api/tramites             - Listar tramites del workspace actual
 * - POST /api/tramites             - Crear nuevo tramite
 * - PUT  /api/tramites/:id         - Actualizar tramite
 * - DELETE /api/tramites/:id       - Eliminar tramite
 * 
 * API DE DOCUMENTOS:
 * - GET  /api/tramites/:id/documentos           - Listar documentos de un tramite
 * - POST /api/tramites/:id/documentos           - Subir documento
 * - DELETE /api/tramites/:id/documentos/:docId  - Eliminar documento
 * - POST /api/tramites/:id/documentos/link      - Agregar link como fuente
 * 
 * API DE CHAT (con streaming):
 * - POST /api/chat                 - Enviar mensaje y recibir respuesta (streaming)
 * - GET  /api/tramites/:id/mensajes - Obtener historial de mensajes
 * 
 * API DE GENERACION:
 * - POST /api/generar-documento    - Generar documento con IA
 * - GET  /api/tramites/:id/documentos-generados - Listar documentos generados
 * - GET  /api/documentos-generados/:id/preview  - Obtener preview del documento
 * 
 * API DE AUDITORIA:
 * - GET  /api/tramites/:id/alertas - Obtener alertas de auditoria
 * - POST /api/verificar-renaper    - Verificar identidad con RENAPER
 * 
 * API DE CONFIGURACION:
 * - GET  /api/config               - Obtener configuracion del usuario
 * - PUT  /api/config               - Actualizar configuracion
 * 
 * VARIABLES DE ENTORNO REQUERIDAS:
 * - OPENAI_API_KEY      - Clave de API de OpenAI (o modelo similar)
 * - DATABASE_URL        - URL de la base de datos
 * - STORAGE_URL         - URL del storage para documentos
 * - RENAPER_API_KEY     - Clave de API de RENAPER (opcional)
 * - NEXTAUTH_SECRET     - Secret para autenticacion
 * 
 * @author OfiSolve Team
 * @version 3.0.0
 */

import { useState, useEffect, useCallback, useRef } from "react"
import { useTheme } from "next-themes"
import { WelcomeHero } from "@/components/welcome-hero"
import { ofisolveApi } from "@/lib/api"
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar"
import type { 
  CertificacionResponse, 
  ClienteResponse, 
  EquipoMiembroResponse,
  TramiteResponse,
  Usuario,
  Workspace,
  Tramite,
  DocumentoFuente,
  MensajeChat,
  AlertaLegal,
  DocumentoGenerado,
  TipoDocumentoGenerable
} from "@/lib/types"
import {
  Brain,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  FileText,
  FileType2,
  FileImage,
  FileSpreadsheet,
  Link2,
  Moon,
  Sun,
  Plus,
  Send,
  SendHorizontal,
  Trash2,
  X,
  AlertTriangle,
  CheckCircle2,
  BookOpen,
  FileCheck,
  FileCheck2,
  FilePlus,
  Download,
  DownloadCloud,
  Eye,
  Loader2,
  Upload,
  FolderOpen,
  Settings,
  LogOut,
  User,
  UserIcon,
  UserCog,
  Building2,
  Globe,
  HelpCircle,
  Briefcase,
  MoreHorizontal,
  PanelLeftClose,
  PanelLeftOpen,
  PanelRightClose,
  PanelRightOpen,
  Check,
  Stamp,
  ScrollText,
  FileSignature,
  Scale,
  Gavel,
  History,
  Sparkles,
  Zap,
  ArrowRight,
  Search,
  Lock,
  Copy,
  Mail,
  Bell,
  Palette,
  KeyRound,
  UserPlus,
  Users,
  Wand2,
  BrainCircuit,
  ShieldCheck,
  Folder,
  MessageSquare,
  ShieldAlert,
  Bot,
  RotateCw,
  ClipboardList,
  LayoutGrid,
  Menu
} from "lucide-react"

import {
  Sheet,
  SheetContent,
  SheetTrigger,
  SheetTitle,
} from "@/components/ui/sheet"

import { confirmToast, promptToast } from "@/lib/dialogs"

// Nuevos componentes Fase 4
import { LoginView } from "@/components/login-view"
import { NotarialEditor } from "@/components/notarial-editor"
import { NuevoClienteModal } from "@/components/nuevo-cliente-modal"
import { IngesiMotor } from "@/components/ingesi-motor";
import { ChatArea } from "@/components/chat/ChatArea";
import { Sidebar } from "@/components/layout/Sidebar";
import { AuditoriaPanel } from "@/components/layout/AuditoriaPanel";
import { GlobalChatPanel } from "@/components/global-chat-panel";
import { SubirDocumentoModal } from "@/components/modals/SubirDocumentoModal";
import { ConfiguracionModal } from "@/components/modals/ConfiguracionModal";
import { EditarPerfilModal } from "@/components/modals/EditarPerfilModal";
import { CambiarContrasenaModal } from "@/components/modals/CambiarContrasenaModal";
import { NuevoWorkspaceModal } from "@/components/modals/NuevoWorkspaceModal";
import { NuevoTramiteModal } from "@/components/modals/NuevoTramiteModal";
import { PreviewDocumentoModal } from "@/components/modals/PreviewDocumentoModal";
import { DocumentoEditorModal } from "@/components/modals/DocumentoEditorModal";
// @ts-ignore
import ReactMarkdown from "react-markdown"
// @ts-ignore
import remarkGfm from "remark-gfm"


import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuLabel,
  DropdownMenuGroup,
} from "@/components/ui/dropdown-menu"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  ResizablePanelGroup,
  ResizablePanel,
  ResizableHandle,
} from "@/components/ui/resizable"
import { Checkbox } from "@/components/ui/checkbox"
import { Card } from "@/components/ui/card"
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { cn } from "@/lib/utils"

// =============================================================================
// TIPOS E INTERFACES
// =============================================================================// --- Interfaces locales removidas para usar las de @/lib/types ---

/**
 * =============================================================================
 * DATOS DE PRUEBA (MOCKS) - Se reemplazaran por llamadas API
 * =============================================================================
 */

// UUID constante para el tenant de prueba (OfiSolve Demo)
const DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"

// --- Mocks removidos para usar infraestructura real ---

/**
 * TODO: Reemplazar con GET /api/tramites/:id/documentos
 */
// --- Mocks de documentos y mensajes removidos ---

/**
 * Tipos de documentos generables por la IA
 * Estos se muestran en el panel derecho
 */
const tiposDocumentosGenerables: TipoDocumentoGenerable[] = [
  { 
    id: "certificacion_firma", 
    nombre: "Certificación de Firma", 
    descripcion: "Firma en presencia del escribano",
    categoria: 'certificacion',
    icono: 'stamp'
  },
  { 
    id: "certificacion_fotocopia", 
    nombre: "Certificación de Fotocopia", 
    descripcion: "Reproducción fiel de original",
    categoria: 'certificacion',
    icono: 'stamp'
  },
  { 
    id: "autorizacion_viaje", 
    nombre: "Autorización de Viaje", 
    descripcion: "Para menores de edad (Exterior)",
    categoria: 'acta',
    icono: 'scroll'
  },
  { 
    id: "certificado_supervivencia", 
    nombre: "Certificado Supervivencia", 
    descripcion: "Acredita existencia física",
    categoria: 'acta',
    icono: 'signature'
  },
]

/**
 * TODO: Reemplazar con GET /api/tramites/:id/documentos-generados
 */
const documentosGeneradosMock: DocumentoGenerado[] = [
  {
    id: 1001,
    nombre: "Cert_Firma_Horizonte_2026.docx",
    tipo: "firma",
    fechaGeneracion: new Date("2026-04-18T10:30:00"),
    version: 2,
    contenidoPreview: "CERTIFICACIÓN DE FIRMA — En la Ciudad Autónoma de Buenos Aires, a los dieciocho días del mes de abril de 2026, ante mí, Escribano Público...",
    contenido: "CERTIFICACIÓN DE FIRMA\n\nEn la Ciudad Autónoma de Buenos Aires, a los dieciocho días del mes de abril de 2026, ante mí, Escribano Público, se presentó el Sr. representante de CONSTRUCTORA HORIZONTE S.A., CUIT 30-71234567-8, quien firmó en mi presencia el documento que se adjunta.\n\nDOY FE que la firma que antecede es auténtica, habiendo sido puesta en mi presencia por persona a quien identifico.\n\nConste. — Escritura Nº 234/2026"
  },
  {
    id: 1002,
    nombre: "Poder_General_Horizonte.docx",
    tipo: "poder",
    fechaGeneracion: new Date("2026-04-15T14:00:00"),
    version: 1,
    contenidoPreview: "PODER GENERAL AMPLIO — Otorgado por CONSTRUCTORA HORIZONTE S.A. a favor de...",
    contenido: "PODER GENERAL AMPLIO DE ADMINISTRACIÓN Y DISPOSICIÓN\n\nEn la Ciudad Autónoma de Buenos Aires, a los quince días del mes de abril de 2026...\n\nComparece: CONSTRUCTORA HORIZONTE S.A., representada por su Director, según acta de directorio...\n\nConfiere poder general amplio a favor de Dr. [APODERADO], DNI [NÚMERO], para que en su nombre y representación ejerza actos de administración y disposición..."
  },
  {
    id: 1003,
    nombre: "Cert_Fotocopia_Goldi_DNI.docx",
    tipo: "fotocopia",
    fechaGeneracion: new Date("2026-04-20T09:15:00"),
    version: 1,
    contenidoPreview: "CERTIFICACIÓN DE FOTOCOPIA — Certifico que la fotocopia adjunta es reproducción fiel del original...",
    contenido: "CERTIFICACIÓN DE FOTOCOPIA\n\nEn la Ciudad Autónoma de Buenos Aires, a los veinte días del mes de abril de 2026, ante mí, Escribano Público, CERTIFICO que la fotocopia que antecede es REPRODUCCIÓN FIEL del original que he tenido a la vista.\n\nDocumento: DNI de Roberto Carlos Goldi (25.987.654)\n\nConste. Doy fe."
  },
]

/**
 * Chips de sugerencias rapidas para el chat
 * TODO: Pueden ser dinamicos basados en el contexto del tramite
 */
const sugerenciasChips = [
  "Validar Identidad RENAPER",
  "Certificar firma",
  "Autorización de viaje",
  "Certificar fotocopia",
]

// =============================================================================
// COMPONENTE PRINCIPAL
// =============================================================================

export default function OfiSolve() {
  // ---------------------------------------------------------------------------
  // ESTADO DE LA UI
  // ---------------------------------------------------------------------------
  
  /** Estado de visibilidad del panel izquierdo */
  const [panelIzquierdoVisible, setPanelIzquierdoVisible] = useState(true)
  
  /** Estado de visibilidad del panel derecho */
  const [panelDerechoVisible, setPanelDerechoVisible] = useState(true)
  
  /** Tema: gestionado por next-themes via layout.tsx */
  const { theme, setTheme: setNextTheme } = useTheme()
  
  /** Estado del dialogo de subir documento */
  const [dialogSubirDocumento, setDialogSubirDocumento] = useState(false)
  
  /** Estado del dialogo de configuracion */
  const [dialogConfiguracion, setDialogConfiguracion] = useState(false)
  
  /** Estado del dialogo de nuevo workspace */
  const [dialogNuevoWorkspace, setDialogNuevoWorkspace] = useState(false)
  
  /** Estado del dialogo de nuevo tramite */
  const [dialogNuevoTramite, setDialogNuevoTramite] = useState(false)
  
  /** Estado del dialogo de editar perfil */
  const [dialogEditarPerfil, setDialogEditarPerfil] = useState(false)
  
  /** Estado del dialogo de cambiar contrasena */
  const [dialogCambiarContrasena, setDialogCambiarContrasena] = useState(false)
  
  /** Estado del dialogo de previsualizacion de documento */
  const [dialogPreviewDocumento, setDialogPreviewDocumento] = useState(false)
  
  /** Documento seleccionado para preview */
  const [documentoPreview, setDocumentoPreview] = useState<DocumentoGenerado | null>(null)
  
  /** Tab activa en el dialogo de subir documento */
  const [tabSubirDocumento, setTabSubirDocumento] = useState<string>("archivo")
  
  /** Tab activa en el dialogo de configuracion */
  const [tabConfiguracion, setTabConfiguracion] = useState<string>("apariencia")
  
  /** Estado del dropdown de tramites */
  const [dropdownTramitesAbierto, setDropdownTramitesAbierto] = useState(false)
  
  /** Referencia al input de archivo */
  const inputArchivoRef = useRef<HTMLInputElement>(null)
  
  /** Archivos seleccionados para subir */
  const [archivosSeleccionados, setArchivosSeleccionados] = useState<File[]>([])
  
  /** URL del link a agregar */
  const [linkUrl, setLinkUrl] = useState("")
  const [activeTab, setActiveTab] = useState<'asistente' | 'generador'>('asistente')
  
  /** Estado de carga del upload */
  const [subiendoArchivos, setSubiendoArchivos] = useState(false)
  
  /** Referencia al scroll del chat */
  const chatScrollRef = useRef<HTMLDivElement>(null)
  
  /** Referencia al controlador de aborto del chat */
  const abortControllerRef = useRef<AbortController | null>(null)

  // ---------------------------------------------------------------------------
  // ESTADO DE DATOS
  // ---------------------------------------------------------------------------
  
  const [isMounted, setIsMounted] = useState(false)
  const [token, setToken] = useState<string | null>(null)
  const [usuario, setUsuario] = useState<Usuario | null>(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [ollamaStatus, setOllamaStatus] = useState<"online" | "offline" | "error" | "unknown">("unknown")
  const [modelosDisponibles, setModelosDisponibles] = useState<string[]>([])
  const [modeloActivo, setModeloActivo] = useState<string>("ofisolve-notarial")

  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [workspaceActual, setWorkspaceActual] = useState<Workspace | null>(null)
  const [tramiteActual, setTramiteActual] = useState<Tramite | null>(null)
  const [tramites, setTramites] = useState<Tramite[]>([])
  const [documentosFuente, setDocumentosFuente] = useState<DocumentoFuente[]>([])
  const [documentoActual, setDocumentoActual] = useState<DocumentoFuente | null>(null)
  const [mensajesChat, setMensajesChat] = useState<MensajeChat[]>([])
  const [alertasLegales, setAlertasLegales] = useState<AlertaLegal[]>([])
  const [documentosGenerados, setDocumentosGenerados] = useState<DocumentoGenerado[]>([])

  /** Clientes locales cargados */
  const [clientes, setClientes] = useState<ClienteResponse[]>([])
  const [clienteActual, setClienteActual] = useState<ClienteResponse | null>(null)
  
  /** Equipo de la escribania */
  const [equipo, setEquipo] = useState<EquipoMiembroResponse[]>([])
  const [miembroAsignado, setMiembroAsignado] = useState<EquipoMiembroResponse | null>(null)

  const [isNuevoClienteOpen, setIsNuevoClienteOpen] = useState(false)
  const [editorContent, setEditorContent] = useState("")
  
  /** Editor de Documentos */
  const [documentoEditorOpen, setDocumentoEditorOpen] = useState(false)
  const [documentoEditorArchivo, setDocumentoEditorArchivo] = useState<any>(null)

  /** Navegación Jerárquica */
  const [clienteEditandoId, setClienteEditandoId] = useState<number | null>(null)
  const [showArchived, setShowArchived] = useState(false)

  // ---------------------------------------------------------------------------
  // ESTADO DEL CHAT
  // ---------------------------------------------------------------------------
  
  const [inputMensaje, setInputMensaje] = useState("")
  const [enviandoMensaje, setEnviandoMensaje] = useState(false)
  const [datosExtraidos, setDatosExtraidos] = useState<any>(null)

  /** Buscador Global */
  const [globalSearchQuery, setGlobalSearchQuery] = useState("")
  const [globalSearchResults, setGlobalSearchResults] = useState<{clientes: any[], tramites: any[]}>({clientes: [], tramites: []})
  const [isSearchingGlobal, setIsSearchingGlobal] = useState(false)
  const [showGlobalSearch, setShowGlobalSearch] = useState(false)
  const [generandoDocumento, setGenerandoDocumento] = useState<string | null>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [sugerenciasDinamicas, setSugerenciasDinamicas] = useState<string[]>([])
  const [currentAgentNode, setCurrentAgentNode] = useState<string | null>(null)
  const [streamingText, setStreamingText] = useState("")
  const [participaciones, setParticipaciones] = useState<any[]>([])
  const [ejecutandoAuditoria, setEjecutandoAuditoria] = useState(false)
  const [lastOpenedTramiteId, setLastOpenedTramiteId] = useState<number | null>(null)
  const [archivosPorTramite, setArchivosPorTramite] = useState<Record<number, any[]>>({})

  /** Modo del asistente de chat */
  const [modoChat, setModoChat] = useState<"consultas" | "creador">("consultas")

  /** Modal de edición de documentos del Sidebar */
  const [isEditorDocumentoOpen, setIsEditorDocumentoOpen] = useState(false)
  const [documentoAEditar, setDocumentoAEditar] = useState<any>(null)

  // Estado del Chat Global
  const [globalChatOpen, setGlobalChatOpen] = useState(false)
  const [activeGlobalChatId, setActiveGlobalChatId] = useState<number | null>(null)
  const [activeGlobalChatTitle, setActiveGlobalChatTitle] = useState("")
  
  // ---------------------------------------------------------------------------
  // ESTADO DE FORMULARIOS
  // ---------------------------------------------------------------------------
  
  const [formPerfil, setFormPerfil] = useState({ 
    nombre: "", 
    email: "", 
    telefono: "",
    nroMatricula: "",
    escribaniaNombre: "",
    avatar_url: ""
  })
  const [formContrasena, setFormContrasena] = useState({ actual: "", nueva: "", confirmar: "" })
  const [formWorkspace, setFormWorkspace] = useState({ nombre: "", descripcion: "" })
  const [formTramite, setFormTramite] = useState({ nombre: "", tipo: "" })

  // ---------------------------------------------------------------------------
  // EFECTOS DE INICIALIZACIÓN
  // ---------------------------------------------------------------------------

  // Montaje único y recuperación de sesión
  useEffect(() => {
    setIsMounted(true)
    const storedToken = localStorage.getItem("ofisolve_token") || sessionStorage.getItem("ofisolve_token")
    if (storedToken) {
      setToken(storedToken)
      ofisolveApi.setToken(storedToken)
    }
  }, [])

  // Comprobación de estado de Ollama (Migrado a React Query)
  useQuery({
    queryKey: ["ollamaStatus"],
    queryFn: async () => {
      try {
        const health = await ofisolveApi.checkHealth();
        setOllamaStatus(health?.ollama?.status || "unknown");
        
        if (health?.ollama?.status === "online") {
          try {
            const modelos = await ofisolveApi.obtenerModelos();
            if (modelos && modelos.length > 0) {
              setModelosDisponibles(modelos);
              if (!modelos.includes(modeloActivo)) {
                setModeloActivo(modelos[0]);
              }
            }
          } catch (e) {
            console.error("No se pudieron obtener modelos", e);
          }
        }
        return health;
      } catch (e) {
        setOllamaStatus("error");
        return { ollama: { status: "error" } };
      }
    },
    refetchInterval: 30000, // Reemplaza al setInterval
  })


  // Carga de perfil y datos globales
  useEffect(() => {
    if (!isMounted || !token) return

    ofisolveApi.obtenerPerfil()
      .then(u => {
        setUsuario(u)
        setIsAuthenticated(true)
      })
      .catch(err => {
        console.error("Error cargando perfil:", err)
        // Solo desloguear si es estrictamente un error de expiración de token
        // Si el backend se reinicia (network error), mantenemos el token para reconectar
        if (err.message && err.message.includes("Sesión expirada")) {
          setIsAuthenticated(false)
          setToken(null)
          localStorage.removeItem("ofisolve_token")
          sessionStorage.removeItem("ofisolve_token")
        } else {
          // El token sigue siendo válido, pero el servidor está inaccesible
          setIsAuthenticated(true)
        }
      })

    ofisolveApi.obtenerWorkspaces()
      .then(data => {
        const mappedWorkspaces: Workspace[] = data.map(w => ({
          id: w.id.toString(),
          tenant_id: DEFAULT_TENANT_ID,
          nombre: w.nombre,
          descripcion: w.descripcion,
          color: 'blue',
          tramitesCount: w.tramites?.length || 0,
          ultimaActividad: new Date(w.fecha_creacion)
        }))
        setWorkspaces(mappedWorkspaces)
        
        if (mappedWorkspaces.length > 0) {
          const w = mappedWorkspaces[0]
          setWorkspaceActual(w)
          
          ofisolveApi.obtenerTramites(Number(w.id))
            .then(data => {
              const parsed: Tramite[] = data.map(t => ({
                id: t.id,
                tenant_id: DEFAULT_TENANT_ID,
                nombre: t.nombre,
                estado: t.estado as any,
                tipo: t.tipo,
                workspaceId: t.workspace_id.toString(),
                clienteId: t.cliente_id,
                fechaCreacion: new Date(t.fecha_creacion),
                fechaActualizacion: new Date(t.fecha_actualizacion)
              }))
              setTramites(parsed)
              // Auto-selección desactivada para mantener WelcomeHero
            })
            .catch(err => console.error("Error cargando trámites:", err))
        }
      })
      .catch(err => console.error("Error cargando workspaces:", err))
  }, [isMounted, token])

  // --- Efecto: Búsqueda Global (Debounced) ---
  useEffect(() => {
    if (!workspaceActual?.id) return;
    const delayDebounceFn = setTimeout(() => {
      if (globalSearchQuery.length >= 2) {
        setIsSearchingGlobal(true)
        ofisolveApi.buscarGlobal(Number(workspaceActual.id), globalSearchQuery)
          .then(res => {
            setGlobalSearchResults(res)
            setShowGlobalSearch(true)
            setIsSearchingGlobal(false)
          })
          .catch(err => {
            console.error(err)
            setIsSearchingGlobal(false)
          })
      } else {
        setGlobalSearchResults({clientes: [], tramites: []})
        setShowGlobalSearch(false)
      }
    }, 300)

    return () => clearTimeout(delayDebounceFn)
  }, [globalSearchQuery, workspaceActual])

  // --- Efecto: Cargar Mensajes al Seleccionar Cliente o Cambiar Modo ---
  useEffect(() => {
    if (!clienteActual || !usuario) return;

    // Resetear chat al cambiar de cliente o de modo
    setMensajesChat([]);
    setStreamingText("");
    setCurrentAgentNode("");

    const getSaludoInicial = (cliente: any, modo: string) => {
      return modo === "consultas" 
        ? `¡Hola! Soy tu Asesor Notarial Virtual. Estoy aquí para resolver tus dudas legales y revisar la normativa para los trámites de ${cliente.nombre_completo}.` 
        : `¡Hola! Soy tu Redactor Notarial. ¿Qué tipo de documento o certificación redactamos hoy para ${cliente.nombre_completo}?`;
    };

    ofisolveApi.obtenerHistorialChat(clienteActual.id, modoChat)
      .then(historial => {
        if (historial && historial.length > 0) {
          const mensajes: MensajeChat[] = historial.map((m: any) => ({
            id: m.id,
            tipo: m.role === 'user' ? 'usuario' : 'ia',
            contenido: m.contenido,
            timestamp: new Date(m.timestamp),
          }));
          setMensajesChat(mensajes);
        } else {
          setMensajesChat([{
            id: Date.now(),
            tipo: "ia",
            contenido: getSaludoInicial(clienteActual, modoChat),
            timestamp: new Date()
          }]);
        }
      })
      .catch(err => {
        console.error("Error cargando historial de chat:", err)
        setMensajesChat([{
            id: Date.now(),
            tipo: "ia",
            contenido: getSaludoInicial(clienteActual, modoChat),
            timestamp: new Date()
          }]);
      });
  }, [clienteActual?.id, usuario?.id, modoChat]);

  const handleLimpiarChat = async () => {
    if (!clienteActual) return;
    setMensajesChat([{
      id: Date.now(),
      tipo: "ia",
      contenido: modoChat === "consultas" 
        ? `¡Hola! Soy tu Asesor Notarial Virtual. Estoy aquí para resolver tus dudas legales y revisar la normativa para los trámites de ${clienteActual.nombre_completo}.` 
        : `¡Hola! Soy tu Redactor Notarial. ¿Qué tipo de documento o certificación redactamos hoy para ${clienteActual.nombre_completo}?`,
      timestamp: new Date()
    }]);
    await ofisolveApi.limpiarHistorialChat(clienteActual.id, modoChat).catch(() => {});
  };

  // Carga de contexto de Workspace
  useEffect(() => {
    if (workspaceActual?.id && token) {
      const wsId = Number(workspaceActual.id)
      if (!isNaN(wsId)) {
        ofisolveApi.obtenerTramites(wsId)
          .then(data => {
            const parsed = data.map(t => ({
              id: t.id,
              tenant_id: DEFAULT_TENANT_ID,
              nombre: t.nombre,
              estado: t.estado as any,
              tipo: t.tipo,
              workspaceId: t.workspace_id.toString(),
              clienteId: t.cliente_id,
              fechaCreacion: new Date(t.fecha_creacion),
              fechaActualizacion: new Date(t.fecha_actualizacion)
            }))
            setTramites(parsed)
            // Auto-selección desactivada para mantener WelcomeHero
          })
        
        ofisolveApi.setWorkspace(wsId)
        ofisolveApi.obtenerClientes(wsId).then(setClientes)
        ofisolveApi.obtenerEquipo(wsId).then(setEquipo)
        
        ofisolveApi.obtenerFuentesRag(wsId).then(data => {
          setDocumentosFuente(data.map((f: any) => ({
            id: f.id,
            nombre: f.titulo || f.nombre || "Documento",
            tipo: f.tipo,
            url: f.fuente || f.path || "",
            seleccionado: true,
            fechaSubida: new Date()
          })))
        }).catch(() => {}) // No bloquear si no hay documentos aún
      }
    }
  }, [workspaceActual, token])

  // Sincronizar form perfil
  useEffect(() => {
    if (usuario) {
      setFormPerfil({
        nombre: usuario.nombre_completo || usuario.nombre || "",
        email: usuario.email || "",
        telefono: usuario.telefono || "",
        nroMatricula: usuario.nroMatricula || "",
        escribaniaNombre: usuario.escribaniaNombre || "",
        avatar_url: usuario.avatar_url || ""
      })
    }
  }, [usuario])

  // Tema gestionado por next-themes en layout.tsx — no se necesita useEffect manual

  // Carga de participaciones y Saludo Contextual
  useEffect(() => {
    if (tramiteActual && token) {
      const tid = tramiteActual.id
      
      // 1. Cargar Participaciones (Entidades Reales)
      ofisolveApi.obtenerParticipaciones(tid)
        .then(data => {
          setParticipaciones(data.clientes || [])
          // datosExtraidos ya no se mockea desde la BD.
        })
        .catch(err => console.error("Error cargando participaciones:", err))

      // 2. Cargar Documentos Generados Reales (reemplaza mocks)
      ofisolveApi.obtenerDocumentosGenerados(tid)
        .then(docs => {
          if (docs && docs.length > 0) {
            setDocumentosGenerados(docs.map((d: any) => ({
              id: d.id,
              nombre: d.nombre,
              tipo: d.tipo,
              fechaGeneracion: new Date(d.fechaGeneracion),
              version: d.version || 1,
              contenidoPreview: d.contenidoPreview || "",
              contenido: d.contenidoPreview || "",
            })))
          }
        })
        .catch(() => {}) // No bloquear si no hay documentos aun
    }
  }, [tramiteActual, token])
  
  useEffect(() => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight
    }
  }, [mensajesChat])

  /**
   * Scroll automatico al final del chat cuando hay nuevos mensajes
   */
  useEffect(() => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight
    }
  }, [mensajesChat])

  // ---------------------------------------------------------------------------
  // HANDLERS DE TEMA Y UI
  // ---------------------------------------------------------------------------

  /**
   * Alterna entre tema claro y oscuro via next-themes
   */
  const toggleTheme = useCallback(() => {
    setNextTheme(theme === "light" ? "dark" : "light")
  }, [theme, setNextTheme])

  /**
   * Cierra la sesion del usuario
   */
  const handleLogout = useCallback(() => {
    localStorage.removeItem("ofisolve_token")
    sessionStorage.removeItem("ofisolve_token")
    setToken(null)
    toast.success("Sesion cerrada correctamente")
  }, [])

  // ---------------------------------------------------------------------------
  // HANDLERS DE CHAT
  // ---------------------------------------------------------------------------

  /**
   * Envia un mensaje al chat e inicia el flujo de streaming SSE
   */
  const enviarMensaje = useCallback(async (overrideText?: string, fuentesIds?: number[]) => {
    const textoUsuario = overrideText || inputMensaje
    if (!textoUsuario?.trim() || enviandoMensaje || !clienteActual) return
    
    // 1. Limpiar input y estado de carga inmediatamente
    setInputMensaje("")
    setEnviandoMensaje(true)
    setIsStreaming(true)
    setCurrentAgentNode("Ofuscando")
    setSugerenciasDinamicas([])

    // Crear nuevo AbortController
    abortControllerRef.current = new AbortController()

    // 2. Preparar Mensaje de Usuario
    const nuevoMensaje: MensajeChat = {
      id: Date.now(),
      tipo: "usuario",
      contenido: textoUsuario,
      timestamp: new Date()
    }
    
    // 3. Preparar Placeholder de Respuesta de IA
    const aiMessageId = Date.now() + 1
    const placeholderIA: MensajeChat = {
      id: aiMessageId,
      tipo: "ia",
      contenido: "",
      timestamp: new Date()
    }

    setMensajesChat(prev => [...prev, nuevoMensaje, placeholderIA])

    let accumulatedText = ""
    
    try {
      const tenantId = workspaceActual?.tenant_id || usuario?.tenant_id || "00000000-0000-0000-0000-000000000001"
      
      const history = mensajesChat
        .filter(m => m.contenido && m.contenido.trim() !== "")
        .slice(-10)
        .map(m => ({
          role: m.tipo === "usuario" ? "user" : "assistant",
          contenido: m.contenido
        }))

      // (B) Persistir mensaje del usuario en DB
      if (clienteActual) {
        ofisolveApi.guardarMensajeChat(clienteActual.id, 'user', textoUsuario, modoChat).catch(() => {});
      }

      // Usar cliente_id + modo como thread_id para colecciones RAG
      const threadId = clienteActual ? `cliente_${clienteActual.id}_${modoChat}` : tenantId;

      await ofisolveApi.streamTramiteChat(
        textoUsuario,
        threadId,
        tenantId,
        history,
        modeloActivo,
        (event) => {
          if (event.event === "estado") {
            setCurrentAgentNode(event.mensaje || event.nodo)
          } 
          else if (event.event === "token") {
            accumulatedText += event.texto;
            // setStreamingText(accumulatedText);
            // No actualizamos mensajesChat intermedio para que no "escriba mientras piensa".
          }
          else if (event.event === "finalizado") {
            setIsStreaming(false)
            setCurrentAgentNode(null)
            
            const finalText = event.texto_completo || accumulatedText
            if (event.texto_completo) {
              setMensajesChat(prev => prev.map(m => 
                m.id === aiMessageId ? { ...m, contenido: event.texto_completo } : m
              ))
              accumulatedText = event.texto_completo
            }

            // (B) Persistir respuesta de la IA en DB
            if (clienteActual && finalText) {
              ofisolveApi.guardarMensajeChat(clienteActual.id, 'assistant', finalText, modoChat).catch(() => {});
            }

            // --- FASE 3: EXTRACCIÓN DE DATOS ESTRUCTURADOS (Simulada para MVP) ---
            if (modoChat === "creador" && finalText.includes("<<JSON>>")) {
              try {
                const parts = finalText.split("<<JSON>>")
                const jsonStr = parts[1].split("<</JSON>>")[0]
                const extracted = JSON.parse(jsonStr)
                setDatosExtraidos(extracted)
                toast.success("Se han extraído datos para la plantilla")
              } catch (e) {
                console.error("Error extrayendo JSON:", e)
              }
            }
            setEditorContent(finalText)
          }
          else if (event.event === "sugerencias") {
            if (Array.isArray(event.opciones)) {
              setSugerenciasDinamicas(event.opciones)
            }
          }
          else if (event.event === "error") {
            toast.error(event.mensaje || "Error en el asistente")
            setIsStreaming(false)
            setCurrentAgentNode(null)
            
            setMensajesChat(prev => prev.map(m => 
              m.id === aiMessageId ? { ...m, contenido: "Lo siento, ha ocurrido un error al procesar tu solicitud." } : m
            ))
          }
        },
        modoChat,
        abortControllerRef.current.signal,
        fuentesIds
      )
    } catch (error: any) {
      if (error.name === 'AbortError') {
        toast.info("Generación cancelada por el usuario.")
      } else {
        console.error("Error en chat:", error)
        toast.error("No se pudo contactar con el asistente de IA.")
        setMensajesChat(prev => prev.map(m => 
          m.id === aiMessageId ? { ...m, contenido: "Error de conexión con el motor IA local." } : m
        ))
      }
    } finally {
      setEnviandoMensaje(false)
      setIsStreaming(false)
      setCurrentAgentNode(null)
      abortControllerRef.current = null
    }
  }, [inputMensaje, mensajesChat, clienteActual, tramiteActual, clienteActual, workspaceActual, enviandoMensaje, usuario, modeloActivo, modoChat, documentosFuente])

  /**
   * Cancela la generación de mensaje en curso
   */
  const abortarMensaje = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
  }, [])

  /**
   * Maneja el click en un chip de sugerencia
   */
  const handleChipClick = useCallback((chip: string) => {
    enviarMensaje(chip)
  }, [enviarMensaje])

  /**
   * Abre el editor de documentos para un archivo del Sidebar
   */
  const handleAbrirDocumento = useCallback((archivo: any) => {
    setDocumentoEditorArchivo(archivo)
    setDocumentoEditorOpen(true)
  }, [])

  // ---------------------------------------------------------------------------
  // HANDLERS DE DOCUMENTOS
  // ---------------------------------------------------------------------------

  /**
   * Genera un documento del tipo especificado
   */
  const generarDocumento = useCallback(async (tipoDocumento: string) => {
    if (!tramiteActual) return
    setGenerandoDocumento(tipoDocumento)
    
    try {
      // Mapear el ID del tipo de doc al tipo que espera el backend
      const tipoMap: Record<string, string> = {
        "certificacion_firma": "firma",
        "certificacion_fotocopia": "fotocopia",
        "autorizacion_viaje": "viaje_menores",
        "certificado_supervivencia": "supervivencia",
      }
      
      const tipoBackend = tipoMap[tipoDocumento]
      
      if (!tipoBackend) {
        // Para tipos no certificables aún (poderes, actas, escrituras)
        toast.info(`El tipo "${tipoDocumento}" estará disponible próximamente.`)
        setGenerandoDocumento(null)
        return
      }

      // Usar datos del trámite actual o clienteActual como contexto
      const cert = await ofisolveApi.generarCertificacion(
        {
          nombre_requirente: clienteActual?.nombre_completo || "Juan Carlos Perez",
          dni: clienteActual?.dni || "35123456",
          tipo_documento_a_certificar: tipoBackend as any,
          fuentes_seleccionadas: documentosFuente.filter(d => d.seleccionado).map(d => d.nombre)
        },
        {
          nombre_escribano: usuario?.nombre || "Escribano",
          nro_registro: "123",
        }
      )

      // Agregamos al lateral
      setDocumentosGenerados(prev => [{
        id: Date.now(),
        nombre: cert.ruta_descarga ? cert.ruta_descarga.split(/[\\/]/).pop()! : `Cert_Rapida.docx`,
        tipo: tipoBackend,
        fechaGeneracion: new Date(),
        version: 1,
        certificacionId: cert.ruta_descarga || undefined,
        contenido: cert.texto_generado
      }, ...prev])

      // Agregar alerta si hubo anonimizacion
      if (cert.anonimizacion?.campos_anonimizados > 0) {
         setAlertasLegales(prev => [{
           id: Date.now(),
           tipo: 'success',
           titulo: 'Presidio: Datos Ofuscados',
           descripcion: `Se anonimizaron ${cert.anonimizacion.campos_anonimizados} entidades (${cert.anonimizacion.tipos_detectados.join(", ")}).`
         }, ...prev.filter(a => a.tipo !== 'success')])
      }

      // Mostrar resultado en el chat
      const msg: MensajeChat = {
        id: Date.now(),
        tipo: "ia",
        contenido: `Documento generado exitosamente\n\nTipo: ${tipoDocumento}\nModo: ${cert.modo_llm}\nCampos protegidos: ${cert.anonimizacion?.campos_anonimizados || 0}\n\n---\n${cert.texto_generado}\n---\n\n${cert.archivo_docx ? `Archivo: ${cert.archivo_docx}` : ""}`,
        referencias: [
          { id: 1, texto: "Art. 299-312 CCyCN" },
          { id: 2, texto: "Ley 404 CABA" },
        ],
        timestamp: new Date()
      }
      setMensajesChat(prev => [...prev, msg])

      // --- GUARDAR DATOS EXTRAIDOS (NUEVO) ---
      if (cert.datos_extraidos) {
        setDatosExtraidos(cert.datos_extraidos)
      }

      // Si hay archivo disponible, ofrecer descarga
      if (cert.ruta_descarga) {
        const descargar = await confirmToast("Documento generado. ¿Desea descargar el archivo .docx?")
        if (descargar) {
          await ofisolveApi.descargarDocx(cert.ruta_descarga, cert.archivo_docx || "certificacion.docx")
        }
      }
    } catch (error: any) {
      toast.error(`Error al generar: ${error.message}`)
    } finally {
      setGenerandoDocumento(null)
    }
  }, [usuario?.nombre, clienteActual, documentosFuente, tramiteActual])

  /**
   * Finaliza el tramite aprobando el documento (HITL)
   */
  const handleApproveDocumento = useCallback(async (contenido: string) => {
    if (!tramiteActual || !workspaceActual) return
    
    try {
      await ofisolveApi.aprobarTramite(
        tramiteActual.id,
        contenido
      )
      
      // Actualizar estado local
      setTramiteActual(prev => prev ? { ...prev, estado: 'completado' } : null)
      setTramites(prev => prev.map(t => 
        t.id === tramiteActual.id ? { ...t, estado: 'completado' } : t
      ))
      
      toast.success("Trámite finalizado y documentos persistidos en base de datos.")
    } catch (error: any) {
      console.error("Error en aprobación:", error)
      throw error // Propagar al editor para mostrar el toast de error
    }
  }, [tramiteActual, workspaceActual])

  /**
   * Maneja el cambio de contenido en el editor
   */
  const handleEditorChange = useCallback((contenido: string) => {
    setEditorContent(contenido)
  }, [])

  /**
   * Descarga un documento generado
   */
  const descargarDocumento = useCallback(async (documento: DocumentoGenerado) => {
    try {
      if (documento.certificacionId) {
        const ruta = `/api/v1/generate/descargar/${documento.nombre}`
        await ofisolveApi.descargarDocx(ruta, documento.nombre)
      } else if (documento.url) {
        window.open(documento.url, '_blank')
      } else {
        toast.warning(`El documento "${documento.nombre}" no tiene URL de descarga disponible aún.`)
      }
    } catch (error: any) {
      toast.error(`Error al descargar: ${error.message}`)
    }
  }, [])

  /**
   * Previsualiza un documento generado
   */
  const previsualizarDocumento = useCallback((documento: DocumentoGenerado) => {
    setDocumentoPreview(documento)
    setDialogPreviewDocumento(true)
  }, [])
  
  /**
   * Alterna la seleccion de un documento fuente
   */
  const toggleSeleccionDocumento = useCallback((documentoId: number) => {
    setDocumentosFuente(prev => prev.map(doc => 
      doc.id === documentoId 
        ? { ...doc, seleccionado: !doc.seleccionado }
        : doc
    ))
  }, [])


  /**
   * Maneja la seleccion de archivos para subir
   */
  const handleSeleccionArchivos = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files) {
      setArchivosSeleccionados(Array.from(files))
    }
  }, [])

  /**
   * Sube los archivos seleccionados
   */
  const subirArchivos = useCallback(async () => {
    if (archivosSeleccionados.length === 0 || !workspaceActual) return
    
    setSubiendoArchivos(true)
    
    try {
      for (const archivo of archivosSeleccionados) {
        // (A) Pasar tramite_id para indexar en coleción RAG específica
        await ofisolveApi.subirDocumento(Number(workspaceActual?.id), archivo, tramiteActual?.id)
      }
      
      toast.success(`${archivosSeleccionados.length} archivo(s) subido(s) e indexado(s) en la carpeta`)
      
      // Refrescar lista de documentos
      ofisolveApi.obtenerFuentesRag().then((data: any[]) => {
        const docs = data.map((f: any) => ({
          id: f.id,
          nombre: f.titulo,
          tipo: f.tipo,
          url: f.fuente,
          seleccionado: true,
          fechaSubida: new Date()
        }))
        setDocumentosFuente(docs)
      })

      setArchivosSeleccionados([])
      setDialogSubirDocumento(false)
    } catch (error: any) {
      toast.error(`Error al subir archivos: ${error.message}`)
    } finally {
      setSubiendoArchivos(false)
    }
  }, [archivosSeleccionados, workspaceActual?.id])

  /**
   * Agrega un link como fuente
   */
  const agregarLink = useCallback(async () => {
    if (!linkUrl.trim() || !workspaceActual) return
    
    setSubiendoArchivos(true)
    
    setTimeout(() => {
      const nuevoLink: DocumentoFuente = {
        id: Date.now(),
        nombre: linkUrl,
        tipo: 'link',
        url: linkUrl,
        fechaSubida: new Date(),
        seleccionado: true
      }
      
      setDocumentosFuente(prev => [...prev, nuevoLink])
      setLinkUrl("")
      setSubiendoArchivos(false)
      setDialogSubirDocumento(false)
    }, 1000)
  }, [linkUrl, workspaceActual])

  /**
   * Elimina un documento fuente de la base de datos y del estado local.
   */
  const eliminarDocumento = useCallback(async (documentoId: number) => {
    if (await confirmToast("Estas seguro de eliminar este documento?")) {
      setDocumentosFuente(prev => prev.filter(d => d.id !== documentoId))
    }
  }, [])


  // ---------------------------------------------------------------------------
  // HANDLERS DE NAVEGACION
  // ---------------------------------------------------------------------------

  /**
   * Cambia el workspace actual
   */
  const seleccionarWorkspace = (workspace: Workspace) => {
    if (workspace.id === workspaceActual?.id) return;
    setWorkspaceActual(workspace)
    // Clear all workspace-dependent state to avoid data flash from previous workspace
    setTramiteActual(null)
    setTramites([])
    setMensajesChat([])
    setDocumentosGenerados([])
    setClientes([])
    setClienteActual(null)
    setParticipaciones([])
    setDatosExtraidos(null)
    setArchivosPorTramite({})
  }

  /**
   * Cambia el tramite actual
   */
  const cambiarTramite = useCallback((tramite: Tramite) => {
    setTramiteActual(tramite)
    setDropdownTramitesAbierto(false)
  }, [])

  /**
   * Cierra sesion del usuario
   */
  const cerrarSesion = useCallback(() => {
    localStorage.removeItem("ofisolve_token")
    sessionStorage.removeItem("ofisolve_token")
    setToken(null)
    setUsuario(null)
    setIsAuthenticated(false)
    setWorkspaces([])
    setWorkspaceActual(null)
    setTramiteActual(null)
    setTramites([])
    setClientes([])
    setClienteActual(null)
    setMensajesChat([])
    toast.success("Sesión cerrada correctamente")
  }, [])
  
  /**
   * Guarda los cambios del perfil
   */
  const guardarPerfil = useCallback(async () => {
    try {
      const payload = {
        nombre_completo: formPerfil.nombre,
        nro_matricula: formPerfil.nroMatricula,
        escribania_nombre: formPerfil.escribaniaNombre
      };
      
      const updatedUser = await ofisolveApi.actualizarPerfil(payload);
      
      setUsuario(prev => prev ? ({
        ...prev,
        nombre: updatedUser.nombre_completo,
        nombre_completo: updatedUser.nombre_completo,
        nroMatricula: updatedUser.nro_matricula,
        escribaniaNombre: updatedUser.escribania_nombre
      }) : null);
      
      setDialogEditarPerfil(false)
      toast.success("Perfil actualizado correctamente")
    } catch (error: any) {
      toast.error(`Error al actualizar perfil: ${error.message}`)
    }
  }, [formPerfil])
  
  /**
   * Cambia la contrasena del usuario
   */
  const cambiarContrasena = useCallback(async () => {
    if (formContrasena.nueva !== formContrasena.confirmar) {
      toast.error("Las contraseñas no coinciden")
      return
    }
    setFormContrasena({ actual: "", nueva: "", confirmar: "" })
    setDialogCambiarContrasena(false)
    toast.success("Contraseña actualizada correctamente")
  }, [formContrasena])
  
  /**
   * Crea un nuevo workspace
   */
  const crearWorkspace = useCallback(async () => {
    if (!formWorkspace.nombre.trim()) return
    try {
      const nuevo = await ofisolveApi.crearWorkspace({
        nombre: formWorkspace.nombre,
        descripcion: formWorkspace.descripcion
      })
      const mapped: Workspace = {
        id: nuevo.id.toString(),
        tenant_id: DEFAULT_TENANT_ID,
        nombre: nuevo.nombre,
        descripcion: nuevo.descripcion,
        color: 'blue',
        tramitesCount: 0,
        ultimaActividad: new Date(nuevo.fecha_creacion)
      }
      setWorkspaces(prev => [...prev, mapped])
      setWorkspaceActual(mapped)
      setFormWorkspace({ nombre: "", descripcion: "" })
      setDialogNuevoWorkspace(false)
    } catch (err) {
      console.error(err)
      toast.error("Error al crear el workspace")
    }
  }, [formWorkspace])
  
  /**
   * Crea un nuevo tramite
   */
  const crearTramite = useCallback(async () => {
    if (!formTramite.nombre.trim() || !workspaceActual) {
       toast.warning("Seleccioná un workspace primero")
       return
    }
    
    try {
      const nuevo = await ofisolveApi.crearTramite(Number(workspaceActual?.id), {
        nombre: formTramite.nombre,
        tipo: formTramite.tipo
      })
      
      const mapped: Tramite = {
        id: nuevo.id,
        tenant_id: DEFAULT_TENANT_ID,
        nombre: nuevo.nombre,
        estado: nuevo.estado as any,
        tipo: nuevo.tipo,
        workspaceId: nuevo.workspace_id.toString(),
        fechaCreacion: new Date(nuevo.fecha_creacion),
        fechaActualizacion: new Date(nuevo.fecha_actualizacion)
      }
      
      setTramites(prev => [...prev, mapped])
      setTramiteActual(mapped)
      setFormTramite({ nombre: "", tipo: "" })
      setDialogNuevoTramite(false)
    } catch (err) {
      console.error(err)
      toast.error("Error al crear el trámite")
    }
  }, [formTramite, workspaceActual])

  const handleGuardarMensaje = useCallback(async (mensaje: MensajeChat) => {
    if (!tramiteActual || !workspaceActual) return

    // Guardar como documento del trámite actual
    const nombre = await promptToast("Nombre del documento:", `Respuesta_${new Date().toISOString().slice(0,10)}.txt`)
    
    if (!nombre) return

    try {
      const doc = await ofisolveApi.guardarDocumentoGenerado(
        tramiteActual.id,
        nombre,
        mensaje.contenido
      )
      
      setDocumentosGenerados(prev => [{
        id: doc.id,
        nombre: doc.nombre,
        tipo: doc.tipo,
        fechaGeneracion: new Date(doc.fecha_subida),
        version: 1,
        contenido: mensaje.contenido
      }, ...prev])
      
      toast.success("Documento guardado exitosamente en la carpeta.")
    } catch (error: any) {
      toast.error(`Error al guardar: ${error.message}`)
    }
  }, [tramiteActual, workspaceActual, clienteActual])
  
  /**
   * Acciones de carpeta (Trámites)
   */
  const handleEditarTramite = useCallback((tramite: Tramite) => {
    setFormTramite({ nombre: tramite.nombre, tipo: tramite.tipo });
    setDialogNuevoTramite(true);
  }, []);

  const handleDuplicarTramite = useCallback(async (tramite: Tramite) => {
    if (!workspaceActual) return;
    try {
      const nuevo = await ofisolveApi.crearTramite(Number(workspaceActual.id), {
        nombre: `${tramite.nombre} (Copia)`,
        tipo: tramite.tipo,
        cliente_id: tramite.clienteId
      });
      const mapped: Tramite = {
        id: nuevo.id,
        tenant_id: DEFAULT_TENANT_ID,
        nombre: nuevo.nombre,
        estado: nuevo.estado as any,
        tipo: nuevo.tipo,
        workspaceId: nuevo.workspace_id.toString(),
        clienteId: nuevo.cliente_id,
        fechaCreacion: new Date(nuevo.fecha_creacion),
        fechaActualizacion: new Date(nuevo.fecha_actualizacion)
      };
      setTramites(prev => [...prev, mapped]);
      toast.success("Trámite duplicado correctamente");
    } catch (err) {
      toast.error("Error al duplicar el trámite");
    }
  }, [workspaceActual]);

  const handleExportarHistorial = useCallback(async (tramite: Tramite) => {
    toast.info("Generando reporte de historial...");
    try {
      const historial = mensajesChat.map(m => `[${m.tipo.toUpperCase()}] ${m.contenido}`).join('\n\n');
      const contenido = `Historial de Trámite: ${tramite.nombre}\n\n${historial}`;
      await ofisolveApi.exportarDocumento(
        `Historial_${tramite.nombre.replace(/ /g, '_')}`,
        contenido,
        "pdf"
      );
      toast.success("Historial exportado como PDF");
    } catch (err) {
      toast.error("Error al exportar historial");
    }
  }, [mensajesChat]);

  const handleArchivarTramite = useCallback(async (tramite: Tramite) => {
    try {
      await ofisolveApi.actualizarTramite(tramite.id, { estado: "archivado" });
      setTramites(prev => prev.map(t => t.id === tramite.id ? { ...t, estado: "archivado" } : t));
      if (tramiteActual?.id === tramite.id) {
        setTramiteActual(prev => prev ? { ...prev, estado: "archivado" } : null);
      }
      toast.success("Trámite archivado correctamente");
    } catch (err) {
      toast.error("Error al archivar el trámite");
    }
  }, [tramiteActual]);

  const handleEliminarTramite = useCallback(async (tramite: Tramite) => {
    if (!workspaceActual) return;
    if (!(await confirmToast("¿Está seguro de que desea eliminar este trámite de forma permanente? Se borrarán sus documentos y chat."))) return;
    
    try {
      await ofisolveApi.eliminarTramite(Number(workspaceActual.id), tramite.id);
      setTramites(prev => prev.filter(t => t.id !== tramite.id));
      if (tramiteActual?.id === tramite.id) {
        setTramiteActual(null);
      }
      toast.success("Trámite eliminado permanentemente");
    } catch (err) {
      toast.error("Error al eliminar el trámite");
    }
  }, [tramiteActual, workspaceActual]);

  const handleMoverTramite = useCallback((tramiteId: number, clienteIdDestino: number) => {
    // Buscar tramite para saber cliente origen
    const tramiteAMover = tramites.find(t => t.id === tramiteId);
    if (!tramiteAMover || tramiteAMover.clienteId === clienteIdDestino) return;
    
    const clienteIdOrigen = tramiteAMover.clienteId;

    // Actualizacion optimista
    setTramites(prev => prev.map(t => t.id === tramiteId ? { ...t, clienteId: clienteIdDestino } : t));
    
    let isUndone = false;
    const timeoutId = setTimeout(async () => {
       if (isUndone) return;
       try {
         await ofisolveApi.moverTramite(tramiteId, clienteIdDestino);
       } catch (err: any) {
         toast.error(`Error al mover carpeta: ${err.message}`);
         // Revert
         setTramites(prev => prev.map(t => t.id === tramiteId ? { ...t, clienteId: clienteIdOrigen } : t));
       }
    }, 10000);

    toast.success("Carpeta movida a otro cliente", {
       duration: 10000,
       action: {
         label: "Deshacer",
         onClick: () => {
           isUndone = true;
           clearTimeout(timeoutId);
           setTramites(prev => prev.map(t => t.id === tramiteId ? { ...t, clienteId: clienteIdOrigen } : t));
           toast.info("Acción deshecha");
         }
       }
    });
  }, [tramites]);

  const handleMoverDocumento = useCallback((docId: number, tramiteIdDestino: number) => {
    // Identificar tramite origen
    const tramiteOrigenStr = Object.keys(archivosPorTramite).find(tid => archivosPorTramite[Number(tid)]?.some(d => d.id === docId));
    if (!tramiteOrigenStr) return;
    const tramiteIdOrigen = Number(tramiteOrigenStr);
    
    if (tramiteIdOrigen === tramiteIdDestino) return;
    
    const docAMover = archivosPorTramite[tramiteIdOrigen].find(d => d.id === docId);
    if (!docAMover) return;

    // Actualizacion optimista
    setArchivosPorTramite(prev => {
      const prevOrigen = prev[tramiteIdOrigen] || [];
      const prevDestino = prev[tramiteIdDestino] || [];
      return {
        ...prev,
        [tramiteIdOrigen]: prevOrigen.filter(d => d.id !== docId),
        [tramiteIdDestino]: [...prevDestino, docAMover]
      };
    });

    let isUndone = false;
    const timeoutId = setTimeout(async () => {
      if (isUndone) return;
      try {
        await ofisolveApi.moverDocumento(docId, tramiteIdDestino);
      } catch (err: any) {
         toast.error("Error al mover documento");
         // Revert
         setArchivosPorTramite(prev => {
           const currentOrigen = prev[tramiteIdOrigen] || [];
           const currentDestino = prev[tramiteIdDestino] || [];
           return {
             ...prev,
             [tramiteIdDestino]: currentDestino.filter(d => d.id !== docId),
             [tramiteIdOrigen]: [...currentOrigen, docAMover]
           };
         });
      }
    }, 10000);

    toast.success("Documento movido", {
       duration: 10000,
       action: {
         label: "Deshacer",
         onClick: () => {
           isUndone = true;
           clearTimeout(timeoutId);
           setArchivosPorTramite(prev => {
             const currentOrigen = prev[tramiteIdOrigen] || [];
             const currentDestino = prev[tramiteIdDestino] || [];
             return {
               ...prev,
               [tramiteIdDestino]: currentDestino.filter(d => d.id !== docId),
               [tramiteIdOrigen]: [...currentOrigen, docAMover]
             };
           });
           toast.info("Acción deshecha");
         }
       }
    });
  }, [archivosPorTramite])

  const handleExploreKnowledge = useCallback(async () => {
    if (!workspaceActual) {
      toast.error("Debe seleccionar un workspace primero");
      return;
    }

    // Buscamos si ya existe el trámite genérico de Consultas
    const tramiteExistente = tramites.find(t => t.nombre === "Consultas Normativas Generales" && t.workspaceId === workspaceActual.id);
    if (tramiteExistente) {
      setTramiteActual(tramiteExistente);
      setActiveTab('asistente');
      return;
    }

    // Si no existe, creamos uno sin cliente asociado
    try {
      const nuevo = await ofisolveApi.crearTramite(Number(workspaceActual.id), {
        nombre: "Consultas Normativas Generales",
        tipo: "consulta_legal"
      });
      const nuevoTramite: Tramite = {
        id: nuevo.id,
        tenant_id: DEFAULT_TENANT_ID,
        nombre: nuevo.nombre,
        estado: nuevo.estado as any,
        tipo: nuevo.tipo,
        workspaceId: nuevo.workspace_id.toString(),
        fechaCreacion: new Date(nuevo.fecha_creacion),
        fechaActualizacion: new Date(nuevo.fecha_actualizacion)
      };
      setTramites(prev => [...prev, nuevoTramite]);
      setTramiteActual(nuevoTramite);
      setActiveTab('asistente');
      toast.success("Área de Consultas Legales inicializada");
    } catch (error: any) {
      toast.error("Error al iniciar Biblioteca Legal: " + error.message);
    }
  }, [tramiteActual, workspaceActual, clienteActual])

  const handleEjecutarAuditoria = async () => {
    if (!tramiteActual) return;
    setEjecutandoAuditoria(true);
    setDatosExtraidos(null);
    try {
      const resultado = await ofisolveApi.ejecutarAuditoriaLegal(tramiteActual.id);
      if (resultado.clientes) {
        setDatosExtraidos(resultado);
        if (resultado.mensaje) {
          toast.info(resultado.mensaje);
        } else {
          toast.success("Auditoría Legal completada");
        }
      } else {
        toast.error(resultado.mensaje || "Error ejecutando auditoría");
      }
    } catch (err) {
      toast.error("Error conectando con el motor de auditoría");
    } finally {
      setEjecutandoAuditoria(false);
    }
  };

  // ---------------------------------------------------------------------------
  // FUNCIONES DE UTILIDAD
  // ---------------------------------------------------------------------------

  /**
   * Retorna el icono apropiado segun el tipo de documento
   */
  const getIconoDocumento = (tipo: string) => {
    switch (tipo) {
      case "pdf":
        return <FileText className="h-4 w-4 text-muted-foreground" />
      case "word":
        return <FileType2 className="h-4 w-4 text-muted-foreground" />
      case "link":
        return <Link2 className="h-4 w-4 text-muted-foreground" />
      case "image":
        return <FileImage className="h-4 w-4 text-muted-foreground" />
      case "excel":
        return <FileSpreadsheet className="h-4 w-4 text-muted-foreground" />
      case "legislacion":
        return <Gavel className="h-4 w-4 text-muted-foreground" />
      case "procedimiento":
        return <BookOpen className="h-4 w-4 text-muted-foreground" />
      default:
        return <FileText className="h-4 w-4 text-muted-foreground" />
    }
  }
  
  /**
   * Retorna el icono apropiado segun el tipo de documento generable
   */
  const getIconoGenerable = (icono: TipoDocumentoGenerable['icono']) => {
    switch (icono) {
      case "stamp":
        return <Stamp className="h-5 w-5" />
      case "signature":
        return <FileSignature className="h-5 w-5" />
      case "scroll":
        return <ScrollText className="h-5 w-5" />
      case "scale":
        return <Scale className="h-5 w-5" />
      case "gavel":
        return <Gavel className="h-5 w-5" />
      default:
        return <FileCheck className="h-5 w-5" />
    }
  }

  /**
   * Retorna los estilos de alerta segun el tipo usando clases DS
   */
  const getAlertaEstilo = (tipo: string) => {
    switch (tipo) {
      case "warning":
        return {
          bg: "ds-panel-warning",
          border: "",
          icon: <AlertTriangle className="h-4 w-4" style={{ color: 'var(--color-warning)' }} />,
          titleColor: "font-semibold",
        }
      case "success":
        return {
          bg: "ds-panel-success",
          border: "",
          icon: <CheckCircle2 className="h-4 w-4" style={{ color: 'var(--color-success)' }} />,
          titleColor: "font-semibold",
        }
      case "info":
        return {
          bg: "ds-panel-info",
          border: "",
          icon: <BookOpen className="h-4 w-4" style={{ color: 'var(--color-info)' }} />,
          titleColor: "font-semibold",
        }
      case "error":
        return {
          bg: "ds-panel-danger",
          border: "",
          icon: <AlertTriangle className="h-4 w-4" style={{ color: 'var(--color-danger)' }} />,
          titleColor: "font-semibold",
        }
      default:
        return {
          bg: "bg-muted",
          border: "border-border",
          icon: <FileText className="h-4 w-4 text-muted-foreground" />,
          titleColor: "text-foreground",
        }
    }
  }

  /**
   * Formatea la fecha de generacion de un documento
   */
  const formatearFecha = (fecha: Date | string) => {
    const d = fecha instanceof Date ? fecha : new Date(fecha);
    return new Intl.DateTimeFormat('es-AR', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit'
    }).format(d)
  }

  /**
   * Formatea el tamano de archivo
   */
  const formatearTamano = (bytes?: number) => {
    if (!bytes) return ''
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  /**
   * Obtiene el estado del tramite con estilo
   */
  const getEstadoTramite = (estado?: Tramite['estado'] | string) => {
    switch (estado) {
      case 'borrador':
        return { label: 'Borrador', variant: 'secondary' as const }
      case 'en_progreso':
      case 'abierto':
        return { label: 'En progreso', variant: 'default' as const }
      case 'completado':
        return { label: 'Completado', variant: 'outline' as const }
      case 'archivado':
        return { label: 'Archivado', variant: 'secondary' as const }
      default:
        return { label: estado || 'Desconocido', variant: 'secondary' as const }
    }
  }
  
  /**
   * Cuenta documentos seleccionados
   */
  const documentosSeleccionadosCount = documentosFuente.filter(d => d.seleccionado).length

  // ---------------------------------------------------------------------------
  // RENDERIZADO
  // ---------------------------------------------------------------------------

  if (!isMounted) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-10 w-10 animate-spin text-primary" />
          <p className="text-sm font-medium text-muted-foreground">Iniciando OfiSolve ERP...</p>
        </div>
      </div>
    )
  }

  if (!token && isAuthenticated === false) {
    return <LoginView onLogin={(newToken: string, keepSignedIn: boolean) => {
      if (keepSignedIn) {
        localStorage.setItem("ofisolve_token", newToken)
      } else {
        sessionStorage.setItem("ofisolve_token", newToken)
      }
      setToken(newToken)
      setIsAuthenticated(true)
    }} />
  }

  return (
    <div className="flex h-screen w-full flex-col overflow-hidden bg-background">
      {/* =================================================================
          HEADER PRINCIPAL
          Contiene: Logo, selector workspace, usuario, acciones globales
          ================================================================= */}
      <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-card px-4">
        {/* Seccion Izquierda: Toggle panel + Logo + Workspace */}
        <div className="flex items-center gap-3">
          {/* Menu Hamburguesa Mobile (Sheet) */}
          <div className="lg:hidden flex items-center">
            <Sheet>
              <SheetTrigger asChild>
                <Button variant="ghost" size="icon" className="h-9 w-9 shrink-0 rounded-md lg:hidden" onClick={() => setSidebarAbierto(!sidebarAbierto)}>
                  <Menu className="h-5 w-5" />
                </Button>
              </SheetTrigger>
              <SheetContent side="left" className="p-0 w-80">
                <SheetTitle className="sr-only">Menú de Navegación</SheetTitle>
                <Sidebar
                  clientes={clientes}
                  tramites={tramites}
                  workspaceActual={workspaceActual}
                  clienteActual={clienteActual}
                  setClienteActual={setClienteActual}
                  tramiteActual={tramiteActual}
                  setTramiteActual={setTramiteActual}
                  setClienteEditandoId={setClienteEditandoId}
                  setIsNuevoClienteOpen={setIsNuevoClienteOpen}
                  setIsNuevoTramiteOpen={setDialogNuevoTramite}
                  archivosPorTramite={archivosPorTramite}
                  setArchivosPorTramite={setArchivosPorTramite}
                  usuario={usuario}
                  documentoActual={documentoActual}
                  setDocumentoActual={setDocumentoActual}
                  onAbrirDocumento={handleAbrirDocumento}
                  onOpenGlobalChat={(id, title) => {
                    setActiveGlobalChatId(id)
                    setActiveGlobalChatTitle(title)
                    setGlobalChatOpen(true)
                  }}
                />
              </SheetContent>
            </Sheet>
          </div>

          {/* Toggle Panel Izquierdo (Desktop) */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setPanelIzquierdoVisible(!panelIzquierdoVisible)}
            className="hidden rounded-lg lg:flex"
            aria-label={panelIzquierdoVisible ? "Ocultar panel de fuentes" : "Mostrar panel de fuentes"}
          >
            {panelIzquierdoVisible ? (
              <PanelLeftClose className="h-4 w-4" />
            ) : (
              <PanelLeftOpen className="h-4 w-4" />
            )}
          </Button>
          
          {/* Logo */}
          <div className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-background shadow-sm ring-1 ring-border overflow-hidden">
              <img src="/logo-ofisolve.png" alt="OfiSolve Logo" className="h-7 w-7 object-contain dark:brightness-0 dark:invert" />
            </div>
            <span className="hidden text-lg font-bold tracking-tight text-foreground sm:inline">
              OfiSolve
            </span>
          </div>

          {/* Separador */}
          <div className="hidden h-6 w-px bg-border sm:block" />

          {/* Selector de Workspace */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="hidden h-9 items-center gap-2 rounded-md sm:flex px-3">
                <div 
                  className="h-2 w-2 rounded-full bg-primary/60" 
                />
                <span className="max-w-[150px] truncate text-sm font-medium">
                  {workspaceActual?.nombre || "Cargando..."}
                </span>
                <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-64">
              <DropdownMenuLabel>Workspaces</DropdownMenuLabel>
              <DropdownMenuSeparator />
              {workspaces.map((workspace) => (
                <DropdownMenuItem
                  key={workspace.id}
                  onClick={() => seleccionarWorkspace(workspace)}
                  className="cursor-pointer"
                >
                  <div className="flex items-center gap-3">
                    <div className="h-2.5 w-2.5 rounded-full bg-primary/60" />
                    <div className="flex-1">
                      <p className="text-sm font-medium">{workspace.nombre}</p>
                      <p className="text-xs text-muted-foreground">
                        {workspace.tramitesCount} tramites
                      </p>
                    </div>
                  </div>
                </DropdownMenuItem>
              ))}
              <DropdownMenuSeparator />
              <DropdownMenuItem 
                onClick={() => setDialogNuevoWorkspace(true)}
                className="cursor-pointer"
              >
                <Plus className="mr-2 h-4 w-4" />
                Nuevo Workspace
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          <div className="hidden h-6 w-px bg-border sm:block mx-2" />

          {/* TABS DE NAVEGACION */}
          <div className="flex rounded-lg bg-muted/30 p-1 ring-1 ring-border shadow-inner">
            <button 
              onClick={() => setActiveTab('asistente')}
              className={cn(
                "flex items-center gap-1.5 px-4 py-1 text-xs font-semibold transition-all rounded-md",
                activeTab === 'asistente' ? "bg-background text-primary shadow-sm ring-1 ring-border" : "text-muted-foreground hover:text-foreground"
              )}
            >
              <Sparkles className="h-3.5 w-3.5" />
              Asistente IA
            </button>
            <button 
              onClick={() => setActiveTab('generador')}
              className={cn(
                "flex items-center gap-1.5 px-4 py-1 text-xs font-semibold transition-all rounded-md",
                activeTab === 'generador' ? "bg-background text-primary shadow-sm ring-1 ring-border" : "text-muted-foreground hover:text-foreground"
              )}
            >
              <Wand2 className="h-3.5 w-3.5" />
              Motor Ingesis
            </button>
          </div>
        </div>

        {/* Seccion Central: Buscador Maestro */}
        <div className="flex-1 px-4 flex items-center justify-center lg:max-w-2xl mx-auto">
          <Popover open={showGlobalSearch && globalSearchQuery.length >= 2} onOpenChange={setShowGlobalSearch}>
            <PopoverTrigger asChild>
              <div className="w-full relative group">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  {isSearchingGlobal ? (
                    <div className="h-4 w-4 rounded-full border-2 border-primary border-t-transparent animate-spin" />
                  ) : (
                    <Search className="h-4 w-4 text-muted-foreground group-focus-within:text-primary transition-colors" />
                  )}
                </div>
                <Input 
                  type="text"
                  placeholder="Buscar clientes, carpetas, documentos..."
                  value={globalSearchQuery}
                  onChange={(e) => setGlobalSearchQuery(e.target.value)}
                  onFocus={() => {
                    if (globalSearchQuery.length >= 2) setShowGlobalSearch(true)
                  }}
                  className="w-full pl-10 pr-4 py-2 h-9 border border-border/50 rounded-md bg-muted/30 text-foreground placeholder-muted-foreground focus-visible:ring-1 focus-visible:ring-primary focus-visible:bg-background hover:bg-muted/50 transition-all shadow-inner"
                />
              </div>
            </PopoverTrigger>
            <PopoverContent 
              className="w-[500px] p-0 rounded-xl shadow-2xl border-border bg-background overflow-hidden" 
              align="start" 
              sideOffset={8}
              onOpenAutoFocus={(e) => e.preventDefault()}
            >
              <div className="flex flex-col max-h-[400px]">
                {globalSearchResults.clientes.length === 0 && globalSearchResults.tramites.length === 0 && !isSearchingGlobal && (
                  <div className="p-8 text-center text-sm text-muted-foreground">
                    No se encontraron resultados para "{globalSearchQuery}"
                  </div>
                )}
                
                <ScrollArea className="flex-1">
                  {globalSearchResults.clientes.length > 0 && (
                    <div className="p-2">
                      <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                        <Users className="h-3 w-3" />
                        Clientes
                      </div>
                      <div className="flex flex-col gap-1 mt-1">
                        {globalSearchResults.clientes.map(c => (
                          <button
                            key={`cli-${c.id}`}
                            onClick={() => {
                              const fullCliente = clientes.find(cli => cli.id === c.id);
                              if (fullCliente) {
                                setClienteActual(fullCliente);
                                setTramiteActual(null);
                                setShowGlobalSearch(false);
                                setGlobalSearchQuery("");
                              }
                            }}
                            className="flex flex-col text-left px-3 py-2 rounded-lg hover:bg-accent/50 transition-colors group"
                          >
                            <span className="text-sm font-medium text-foreground group-hover:text-primary transition-colors">{c.nombre}</span>
                            <span className="text-xs text-muted-foreground">DNI: {c.dni || 'S/N'}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {globalSearchResults.clientes.length > 0 && globalSearchResults.tramites.length > 0 && (
                    <div className="h-px bg-border my-1 mx-2" />
                  )}

                  {globalSearchResults.tramites.length > 0 && (
                    <div className="p-2">
                      <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                        <Folder className="h-3 w-3" />
                        Carpetas y Trámites
                      </div>
                      <div className="flex flex-col gap-1 mt-1">
                        {globalSearchResults.tramites.map(t => (
                          <button
                            key={`tram-${t.id}`}
                            onClick={() => {
                              const fullTramite = tramites.find(tr => tr.id === t.id);
                              if (fullTramite) {
                                setTramiteActual(fullTramite);
                                if (t.clienteId) {
                                  const c = clientes.find(cli => cli.id === t.clienteId);
                                  if (c) setClienteActual(c);
                                } else {
                                  setClienteActual(null);
                                }
                                setShowGlobalSearch(false);
                                setGlobalSearchQuery("");
                              }
                            }}
                            className="flex flex-col text-left px-3 py-2 rounded-lg hover:bg-accent/50 transition-colors group"
                          >
                            <span className="text-sm font-medium text-foreground group-hover:text-primary transition-colors">{t.nombre}</span>
                            <div className="flex items-center gap-2 mt-0.5">
                              <Badge variant="outline" className="text-[9px] h-4">{t.estado}</Badge>
                            </div>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </ScrollArea>
              </div>
            </PopoverContent>
          </Popover>
        </div>

        {/* Seccion Derecha: Enlaces + Modelo + Auditoria + Usuario */}
        <div className="flex items-center gap-1">
          {/* (Botones removidos a Herramientas Ocultas) */}
          {/* Model Selector */}
          {modelosDisponibles.length > 0 && (
            <div className="hidden lg:block mr-4">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button 
                    variant="outline"
                    className="h-9 rounded-md bg-background/50 border-border/60 hover:border-primary/50 hover:bg-accent/30 text-[11px] font-medium shadow-sm backdrop-blur-sm transition-all duration-200 gap-2 px-4"
                  >
                    <Sparkles className="h-3.5 w-3.5 text-primary" />
                    {modeloActivo?.includes("llama") ? "Llama 3.1 (El más potente)" : modeloActivo?.includes("qwen") ? "Qwen 2.5 (Más rápido)" : modeloActivo}
                    <ChevronDown className="h-3.5 w-3.5 text-muted-foreground ml-1" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-[220px]">
                  <DropdownMenuLabel className="text-[10px] uppercase text-muted-foreground font-bold">Motor de IA</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  {modelosDisponibles.map(mod => {
                    const isLlama = mod.includes("llama");
                    const isQwen = mod.includes("qwen");
                    const label = isLlama ? "Llama 3.1 (El más potente)" : isQwen ? "Qwen 2.5 (Más rápido)" : mod;
                    return (
                      <DropdownMenuItem 
                        key={mod} 
                        className="text-[11px] cursor-pointer flex items-center justify-between py-2"
                        onClick={() => {
                          setModeloActivo(mod);
                          toast.success(`Cambiando a ${label}...`);
                        }}
                      >
                        {label}
                        {modeloActivo === mod && <Check className="h-3.5 w-3.5 text-primary" />}
                      </DropdownMenuItem>
                    );
                  })}
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          )}

          {/* Ollama Status */}
          <div className="hidden sm:flex items-center mr-4">
            <span className={cn(
              "ds-badge text-[10px] font-medium flex items-center gap-1.5 px-2 py-0.5",
              ollamaStatus === "online" || ollamaStatus === "mock" ? "ds-badge-success" :
              ollamaStatus === "offline" || ollamaStatus === "error" ? "ds-badge-warning" :
              "ds-badge-default"
            )}>
              <span className="relative flex h-1.5 w-1.5">
                <span className={cn(
                  "absolute inline-flex h-full w-full animate-ping rounded-full opacity-75",
                  ollamaStatus === "online" || ollamaStatus === "mock" ? "bg-[var(--color-success)]" :
                  ollamaStatus === "offline" || ollamaStatus === "error" ? "bg-[var(--color-warning)]" :
                  "bg-muted-foreground"
                )}></span>
                <span className={cn(
                  "relative inline-flex h-1.5 w-1.5 rounded-full",
                  ollamaStatus === "online" || ollamaStatus === "mock" ? "bg-[var(--color-success)]" :
                  ollamaStatus === "offline" || ollamaStatus === "error" ? "bg-[var(--color-warning)]" :
                  "bg-muted-foreground"
                )}></span>
              </span>
              {ollamaStatus === "online" ? "IA Local Activa" : 
               ollamaStatus === "mock" ? "IA Simulada" :
               ollamaStatus === "offline" || ollamaStatus === "error" ? "IA No Disponible" : 
               "Conectando..."}
            </span>
          </div>



          {/* Toggle Panel Derecho - Solo visible en modo Creador */}
          {modoChat === "creador" && (
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setPanelDerechoVisible(!panelDerechoVisible)}
              className={cn(
                "hidden h-9 w-9 rounded-md lg:flex mr-2",
                panelDerechoVisible && "bg-accent"
              )}
              aria-label={panelDerechoVisible ? "Ocultar panel de trabajo" : "Mostrar panel de trabajo"}
            >
            {panelDerechoVisible ? (
              <PanelRightClose className="h-4 w-4" />
            ) : (
              <PanelRightOpen className="h-4 w-4" />
            )}
          </Button>
          )}

          {/* Menú de Herramientas Avanzadas */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="h-9 gap-2 rounded-md px-3 mr-2">
                <LayoutGrid className="h-4 w-4 text-muted-foreground" />
                <span className="hidden sm:inline text-sm font-medium">Más</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel>Herramientas Ocultas</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem asChild>
                <Link href={`/libro?workspaceId=${workspaceActual?.id || ''}`} className="cursor-pointer flex items-center">
                  <BookOpen className="mr-2 h-4 w-4" />
                  Libro de Requerimientos
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link href={`/memoria?workspaceId=${workspaceActual?.id || ''}`} className="cursor-pointer flex items-center">
                  <BrainCircuit className="mr-2 h-4 w-4" />
                  Memoria Notarial
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link href={`/documentos?workspaceId=${workspaceActual?.id || ''}`} className="cursor-pointer flex items-center">
                  <FileText className="mr-2 h-4 w-4" />
                  Documentos (Crudo)
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link href={`/tramites?workspaceId=${workspaceActual?.id || ''}`} className="cursor-pointer flex items-center">
                  <Folder className="mr-2 h-4 w-4" />
                  Trámites (Crudo)
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link href={`/clientes?workspaceId=${workspaceActual?.id || ''}`} className="cursor-pointer flex items-center">
                  <Users className="mr-2 h-4 w-4" />
                  Clientes (Crudo)
                </Link>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem asChild>
                <Link href={`/auditoria?workspaceId=${workspaceActual?.id || ''}`} className="cursor-pointer flex items-center">
                  <ShieldCheck className="mr-2 h-4 w-4" />
                  Auditoría
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link href={`/administracion?workspaceId=${workspaceActual?.id || ''}`} className="cursor-pointer flex items-center">
                  <Settings className="mr-2 h-4 w-4" />
                  Administración Avanzada
                </Link>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Menu Usuario */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="flex items-center gap-2 pl-2 pr-3 shrink-0 h-9 rounded-md transition-colors hover:bg-accent/50 focus-visible:ring-1 focus-visible:ring-primary/50">
                <Avatar className="h-6 w-6">
                  <AvatarImage src={usuario?.avatar_url || ""} />
                  <AvatarFallback className="bg-primary/10 text-primary text-[10px]">
                    <User className="h-3 w-3" />
                  </AvatarFallback>
                </Avatar>
                <span className="hidden max-w-[120px] truncate text-sm font-medium lg:inline">
                  {usuario?.nombre_completo || usuario?.nombre || "Usuario"}
                </span>
                <ChevronDown className="hidden h-3.5 w-3.5 text-muted-foreground lg:block" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-64">
              {/* Info Usuario */}
              <div className="px-3 py-2">
                <p className="text-sm font-medium text-foreground">{usuario?.nombre_completo || usuario?.nombre || "Cargando..."}</p>
                <p className="text-xs text-muted-foreground">{usuario?.email}</p>
                {(usuario?.escribania_nombre || usuario?.escribaniaNombre) && (
                  <div className="mt-1.5 flex items-center gap-1.5 text-xs text-muted-foreground">
                    <Building2 className="h-3 w-3" />
                    {usuario?.escribania_nombre || usuario?.escribaniaNombre}
                  </div>
                )}
              </div>
              <DropdownMenuSeparator />
              <DropdownMenuGroup>

                <DropdownMenuItem 
                  onClick={() => setDialogConfiguracion(true)}
                  className="cursor-pointer"
                >
                  <Settings className="mr-2 h-4 w-4" />
                  Configuracion
                </DropdownMenuItem>
              </DropdownMenuGroup>
              <DropdownMenuSeparator />
              <DropdownMenuItem 
                onClick={handleLogout}
                className="cursor-pointer text-destructive focus:text-destructive"
              >
                <LogOut className="mr-2 h-4 w-4" />
                Cerrar sesion
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </header>

      {/* =================================================================
          CONTENIDO PRINCIPAL CON PANELES REDIMENSIONABLES
          ================================================================= */}
      <div className="flex flex-1 overflow-hidden">
        <ResizablePanelGroup direction="horizontal" className="flex-1">
          {/* ===============================================================
              PANEL IZQUIERDO - FUENTES DEL CASO
              =============================================================== */}
          {panelIzquierdoVisible && (
            <>
            <ResizablePanel 
                defaultSize={20} 
                minSize={15} 
                maxSize={35}
                className="hidden lg:block overflow-x-hidden"
              >
                <Sidebar
                  clientes={clientes}
                  tramites={tramites}
                  workspaceActual={workspaceActual}
                  clienteActual={clienteActual}
                  setClienteActual={setClienteActual}
                  tramiteActual={tramiteActual}
                  setTramiteActual={setTramiteActual}
                  setClienteEditandoId={setClienteEditandoId}
                  setIsNuevoClienteOpen={setIsNuevoClienteOpen}
                  setIsNuevoTramiteOpen={setDialogNuevoTramite}
                  archivosPorTramite={archivosPorTramite}
                  setArchivosPorTramite={setArchivosPorTramite}
                  usuario={usuario}
                  documentoActual={documentoActual}
                  setDocumentoActual={setDocumentoActual}
                  onAbrirDocumento={handleAbrirDocumento}
                  onOpenGlobalChat={(id, title) => {
                    setActiveGlobalChatId(id)
                    setActiveGlobalChatTitle(title)
                    setGlobalChatOpen(true)
                  }}
                  onMoverTramite={handleMoverTramite}
                  onMoverDocumento={handleMoverDocumento}
                />
              </ResizablePanel>
              <ResizableHandle withHandle className="hidden lg:flex" />
            </>
          )}

          {/* ===============================================================
              AREA CENTRAL - CHAT DEL ASISTENTE
              =============================================================== */}
          <ResizablePanel defaultSize={panelIzquierdoVisible && (panelDerechoVisible && modoChat === "creador") ? 55 : 100}>
            <main className="flex h-full flex-col overflow-hidden bg-background">
              {activeTab === 'asistente' && (
                <ChatArea
                  clienteActual={clienteActual}
                  tramiteActual={tramiteActual}
                  setTramiteActual={setTramiteActual}
                  documentoActual={documentoActual}
                  usuario={usuario}
                  mensajesChat={mensajesChat}
                  setMensajesChat={setMensajesChat}
                  inputMensaje={inputMensaje}
                  setInputMensaje={setInputMensaje}
                  enviarMensaje={enviarMensaje}
                  abortarMensaje={abortarMensaje}
                  enviandoMensaje={enviandoMensaje}
                  isStreaming={isStreaming}
                  currentAgentNode={currentAgentNode}
                  sugerenciasDinamicas={sugerenciasDinamicas}
                  handleGuardarMensaje={handleGuardarMensaje}
                  setDialogSubirDocumento={setDialogSubirDocumento}
                  equipo={equipo}
                  miembroAsignado={miembroAsignado}
                  setMiembroAsignado={setMiembroAsignado}
                  handleEditarTramite={handleEditarTramite}
                  handleDuplicarTramite={handleDuplicarTramite}
                  handleExportarHistorial={handleExportarHistorial}
                  handleEliminarTramite={handleEliminarTramite}
                  formatearFecha={formatearFecha}
                  getEstadoTramite={getEstadoTramite}
                  setIsNuevoClienteOpen={setIsNuevoClienteOpen}
                  onExploreKnowledge={handleExploreKnowledge}
                  modoChat={modoChat}
                  setModoChat={setModoChat}
                  onLimpiarChat={handleLimpiarChat}
                />
              )}

              {activeTab === 'generador' && (
                /* ================================================================
                   MOTOR INGESIS — Generación Notarial Profesional
                   ================================================================ */
                <IngesiMotor
                  clientes={clientes}
                  workspaceActual={workspaceActual}
                  tramiteActual={tramiteActual}
                  clienteActual={clienteActual}
                  participaciones={participaciones}
                  usuario={usuario}
                  ollamaStatus={ollamaStatus}
                  onDocumentoGenerado={async (resultado) => {
                    // 1. Agregar al panel derecho (Documentos Guardados) de forma optimista
                    const nombreArchivo = resultado.archivo_docx || `Cert_${Date.now()}.docx`;
                    setDocumentosGenerados(prev => [{
                      id: Date.now(),
                      nombre: nombreArchivo,
                      tipo: resultado.modo_llm || "docx",
                      fechaGeneracion: new Date(),
                      version: 1,
                      certificacionId: resultado.ruta_descarga || undefined,
                      contenido: resultado.texto_generado || "",
                      contenidoPreview: (resultado.texto_generado || "").substring(0, 200),
                    }, ...prev]);

                    // 2. Mostrar datos extraídos en Panel de Validación
                    if (resultado.datos_extraidos) {
                      setDatosExtraidos(resultado.datos_extraidos);
                    }

                    // 3. Agregar alerta de privacidad si hubo anonimización
                    if (resultado.anonimizacion?.campos_anonimizados > 0) {
                      setAlertasLegales(prev => [{
                        id: Date.now(),
                        tipo: 'success',
                        titulo: 'Presidio: Datos Ofuscados',
                        descripcion: `Se protegieron ${resultado.anonimizacion.campos_anonimizados} campos (${resultado.anonimizacion.tipos_detectados?.join(", ") || "PII"}).`
                      }, ...prev.filter(a => a.tipo !== 'success')]);
                    }

                    // 4. Refrescar árbol de archivos del Sidebar si hay trámite
                    const tidFinal = resultado.tramite_id || tramiteActual?.id;
                    if (tidFinal) {
                      try {
                        const archivos = await ofisolveApi.obtenerArchivosTramite(tidFinal);
                        setArchivosPorTramite(prev => ({ ...prev, [tidFinal]: archivos }));
                      } catch (e) {
                        // no bloquear si falla el refresco
                      }
                    }
                  }}
                />
              )}
            </main>
          </ResizablePanel>

          {/* ===============================================================
              PANEL DERECHO - GENERACION Y AUDITORIA (Solo modo creador)
              =============================================================== */}
          {panelDerechoVisible && modoChat === "creador" && (
            <>
              <ResizableHandle withHandle className="hidden lg:flex" />
              <ResizablePanel 
                defaultSize={25} 
                minSize={20} 
                maxSize={40}
                className="hidden lg:block"
              >
                <aside className="flex h-full min-h-0 flex-col border-l border-border bg-sidebar">
                  {/* Header */}
                  <div className="flex shrink-0 items-center justify-between border-b border-border px-4 py-3">
                    <h2 className="text-sm font-semibold text-foreground">
                      Panel de Trabajo
                    </h2>
                  </div>

                  {/* Contenido scrolleable */}
                  <ScrollArea className="flex-1">
                    <div className="space-y-6 p-4">

                      {/* La edición ahora se realiza exclusivamente en el DocumentoEditorModal gigante para mejor UX */}

                      {/* Seccion: Documentos Generados */}
                      <div>
                        <h3 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                          <FileText className="h-3.5 w-3.5" />
                          Documentos Guardados ({documentosGenerados.length})
                        </h3>
                        {documentosGenerados.length > 0 ? (
                          <div className="space-y-2">
                            {documentosGenerados.map((doc) => (
                              <div
                                key={doc.id}
                                className="rounded-xl border border-border bg-card p-3"
                              >
                                <div className="flex items-start justify-between gap-2">
                                  <div className="min-w-0 flex-1">
                                    <p className="truncate text-sm font-medium text-foreground">
                                      {doc.nombre}
                                    </p>
                                    <p className="text-xs text-muted-foreground">
                                      {formatearFecha(doc.fechaGeneracion)} - v{doc.version}
                                    </p>
                                  </div>
                                </div>
                                <div className="mt-2 flex gap-2">
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    className="h-7 px-2 text-[10px]"
                                    onClick={() => {
                                      setDocumentoEditorArchivo(doc)
                                      setDocumentoEditorOpen(true)
                                    }}
                                  >
                                    <Eye className="mr-1 h-3 w-3" />
                                    Editar
                                  </Button>
                                  <Button
                                    variant="outline"
                                    size="sm"
                                    className="flex-1 rounded-lg text-xs"
                                    onClick={() => descargarDocumento(doc)}
                                  >
                                    <Download className="mr-1.5 h-3 w-3" />
                                    Descargar
                                  </Button>
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="rounded-xl border border-dashed border-border bg-muted/50 p-4 text-center">
                            <FileText className="mx-auto h-8 w-8 text-muted-foreground/50" />
                            <p className="mt-2 text-xs text-muted-foreground">
                              Aun no hay documentos guardados
                            </p>
                          </div>
                        )}
                      </div>

                      {/* Seccion: Panel de Validación de Datos (Auditoría HITL) */}
                      <div className="mb-4">
                        {!datosExtraidos ? (
                           <div className="rounded-xl border border-dashed border-border bg-muted/50 p-4 text-center">
                             <ShieldAlert className="mx-auto h-8 w-8 text-muted-foreground/50 mb-2" />
                             <p className="text-xs text-muted-foreground mb-3">
                               Valida si las entidades extraídas de los PDFs coinciden con los intervinientes registrados.
                             </p>
                             <Button 
                               size="sm" 
                               variant="outline" 
                               onClick={handleEjecutarAuditoria}
                               disabled={ejecutandoAuditoria}
                               className="w-full text-xs font-medium"
                             >
                               {ejecutandoAuditoria ? (
                                 <><Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" /> Auditando...</>
                               ) : (
                                 <><Bot className="mr-2 h-3.5 w-3.5 text-primary" /> Ejecutar Auditoría Legal</>
                               )}
                             </Button>
                           </div>
                        ) : (
                        <div className="animate-in fade-in slide-in-from-top-2 duration-500">
                          <h3 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary">
                            <CheckCircle2 className="h-3.5 w-3.5" />
                            Panel de Validación de Datos
                          </h3>
                          <div className="space-y-3">
                            <div className="rounded-xl border border-primary/10 bg-primary/5 p-4 shadow-sm">
                              <div className="mb-4 flex items-center justify-between border-b border-primary/10 pb-2">
                                <p className="text-[10px] font-bold uppercase tracking-widest text-primary">Auditoría Inteligente</p>
                                <Badge variant="outline" className="bg-background text-[9px] uppercase tracking-tighter">ID {datosExtraidos.tramite_id}</Badge>
                              </div>
                              
                              <div className="space-y-4">
                                {datosExtraidos.clientes.map((cliente: any, idx: number) => {
                                   const matchingCliente = clientes.find(c => c.dni === cliente.dni_cuit);
                                   const isDataCorrect = matchingCliente && matchingCliente.nombre_completo === cliente.nombre;
                                   
                                   return (
                                     <div key={idx} className="relative overflow-hidden rounded-lg border border-border bg-card p-3 shadow-sm transition-all hover:shadow-md">
                                       <div className="flex items-start justify-between gap-3">
                                         <div className="flex-1">
                                           <div className="flex items-center gap-2 mb-1">
                                             <span className="text-[10px] font-bold text-muted-foreground/60 uppercase">{cliente.rol || 'Interviniente'}</span>
                                             {isDataCorrect ? (
                                               <Badge className="bg-emerald-500/10 text-emerald-600 border-emerald-500/20 hover:bg-emerald-500/20 text-[9px] h-4">Validado</Badge>
                                             ) : (
                                               <Badge variant="destructive" className="bg-red-500/10 text-red-600 border-red-500/20 hover:bg-red-500/20 text-[9px] h-4">Discrepancia</Badge>
                                             )}
                                           </div>
                                           <p className="text-sm font-bold text-foreground">{cliente.nombre}</p>
                                           <p className="font-mono text-[11px] text-muted-foreground">{cliente.dni_cuit}</p>
                                         </div>
                                         
                                         <div className="flex flex-col items-center gap-2">
                                           {isDataCorrect ? (
                                             <div className="rounded-full bg-emerald-500/10 p-1.5 ring-1 ring-emerald-500/20">
                                               <Check className="h-4 w-4 text-emerald-600" />
                                             </div>
                                           ) : (
                                             <div className="rounded-full bg-red-500/10 p-1.5 ring-1 ring-red-500/20 animate-pulse">
                                               <AlertTriangle className="h-4 w-4 text-red-600" />
                                             </div>
                                           )}
                                           {!isDataCorrect && (
                                             <Button 
                                               variant="ghost" 
                                               size="sm" 
                                               className="h-6 px-2 text-[10px] text-primary hover:bg-primary/10"
                                               onClick={() => toast.info("Corrigiendo datos con la base central...")}
                                             >
                                               Corregir
                                             </Button>
                                           )}
                                         </div>
                                       </div>
                                       
                                       {/* Mock validation fields */}
                                       <div className="mt-3 grid grid-cols-2 gap-2 border-t border-border/50 pt-2">
                                         <div className="flex items-center gap-1.5">
                                           <div className={cn("h-1.5 w-1.5 rounded-full", isDataCorrect ? "bg-emerald-500" : "bg-red-500")} />
                                           <span className="text-[10px] text-muted-foreground">Estado Civil</span>
                                         </div>
                                         <div className="flex items-center gap-1.5">
                                           <div className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                                           <span className="text-[10px] text-muted-foreground">RENAPER OK</span>
                                         </div>
                                       </div>
                                     </div>
                                   );
                                })}
                              </div>
                              
                              <div className="mt-4 pt-3 border-t border-primary/10 flex justify-end">
                                 <Button 
                                   variant="ghost" 
                                   size="sm" 
                                   onClick={handleEjecutarAuditoria} 
                                   disabled={ejecutandoAuditoria}
                                   className="text-[10px] text-muted-foreground h-6 px-2"
                                 >
                                   <RotateCw className={`h-3 w-3 mr-1 ${ejecutandoAuditoria ? 'animate-spin' : ''}`} />
                                   Re-auditar
                                 </Button>
                               </div>
                             </div>
                           </div>
                        </div>
                        )}
                      </div>

                      {/* Seccion: Herramientas de Carpeta */}
                      <div className="mb-6 animate-in fade-in slide-in-from-top-2 duration-500 delay-100">
                        <h3 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                          <Wand2 className="h-3.5 w-3.5" />
                          Herramientas de Carpeta
                        </h3>
                        <div className="grid grid-cols-1 gap-2">
                          <Button 
                            variant="outline" 
                            className="w-full justify-start text-xs h-9 bg-card hover:bg-muted/50 border-border/60 transition-colors"
                            onClick={() => {
                              toast.info("Analizando riesgos...");
                              setTimeout(() => {
                                toast.success("Análisis completado: Faltan 2 requisitos obligatorios.");
                                setAlertasLegales(prev => [
                                  { id: Date.now(), tipo: 'error', titulo: 'Falta Libre Deuda', descripcion: 'El certificado de Libre Deuda es obligatorio.' },
                                  { id: Date.now() + 1, tipo: 'warning', titulo: 'Asentimiento Conyugal', descripcion: 'Falta asientimiento conyugal del vendedor.' },
                                  ...prev
                                ]);
                              }, 1500);
                            }}
                          >
                            <ClipboardList className="mr-2 h-4 w-4 text-amber-500" />
                            Análisis de Riesgos (Checklist)
                          </Button>
                          <Button 
                            variant="outline" 
                            className="w-full justify-start text-xs h-9 bg-card hover:bg-muted/50 border-border/60 transition-colors"
                            onClick={() => {
                              setActiveTab('generador');
                              toast.success("Redirigiendo a Generador Rápido con contexto cargado.");
                            }}
                          >
                            <FileSignature className="mr-2 h-4 w-4 text-blue-500" />
                            Generar Anexos (UIF/PEP)
                          </Button>
                        </div>
                      </div>

                      {/* Seccion: Alertas de Auditoria Legal */}
                      <div>
                        <h3 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                          <AlertTriangle className="h-3.5 w-3.5" />
                          Auditoria Legal ({alertasLegales.length})
                        </h3>
                        <div className="space-y-2">
                          {alertasLegales.map((alerta) => {
                            const estilo = getAlertaEstilo(alerta.tipo)
                            return (
                              <div
                                key={alerta.id}
                                className={cn(
                                  "rounded-xl border p-3",
                                  estilo.bg,
                                  estilo.border
                                )}
                              >
                                <div className="flex items-start gap-2.5">
                                  <div className="mt-0.5 shrink-0">{estilo.icon}</div>
                                  <div className="min-w-0 flex-1">
                                    <p className={cn("text-sm font-medium", estilo.titleColor)}>
                                      {alerta.titulo}
                                    </p>
                                    <p className="mt-0.5 text-xs text-muted-foreground">
                                      {alerta.descripcion}
                                    </p>
                                  </div>
                                </div>
                              </div>
                            )
                          })}
                        </div>
                      </div>
                    </div>
                  </ScrollArea>
                </aside>
              </ResizablePanel>
            </>
          )}
        </ResizablePanelGroup>
      </div>

      <SubirDocumentoModal
        open={dialogSubirDocumento}
        onOpenChange={setDialogSubirDocumento}
        workspaceId={workspaceActual?.id ? Number(workspaceActual.id) : undefined}
        tramiteId={tramiteActual?.id}
        onSuccess={() => {
          ofisolveApi.obtenerFuentesRag().then((data: any[]) => {
            const docs = data.map((f: any) => ({
              id: f.id,
              nombre: f.titulo,
              tipo: f.tipo,
              url: f.fuente,
              seleccionado: true,
              fechaSubida: new Date()
            }))
            setDocumentosFuente(docs)
          })
        }}
      />

      <ConfiguracionModal
        open={dialogConfiguracion}
        onOpenChange={setDialogConfiguracion}
        onOpenPerfil={() => setDialogEditarPerfil(true)}
        onOpenContrasena={() => setDialogCambiarContrasena(true)}
        workspaceActual={workspaceActual}
        onUpdateJurisdiccion={async (val: string) => {
          if (!workspaceActual) return;
          try {
            await ofisolveApi.actualizarWorkspace(workspaceActual.id, { jurisdiccion: val });
            setWorkspaces(prev => prev.map(w => w.id === workspaceActual.id ? { ...w, jurisdiccion: val } : w));
            setWorkspaceActual({ ...workspaceActual, jurisdiccion: val });
            toast.success("Jurisdicción del workspace actualizada");
          } catch (error: any) {
            toast.error("Error al actualizar la jurisdicción");
          }
        }}
      />

      <EditarPerfilModal
        open={dialogEditarPerfil}
        onOpenChange={setDialogEditarPerfil}
        initialData={formPerfil}
        onSaveAvatar={async (file) => {
          const res = await ofisolveApi.subirAvatar(file);
          setUsuario(prev => prev ? ({ ...prev, avatar_url: res.avatar_url }) : null);
          setFormPerfil(prev => ({ ...prev, avatar_url: res.avatar_url }));
        }}
        onSave={async (datos) => {
          const updatedUser = await ofisolveApi.actualizarPerfil({
            nombre_completo: datos.nombre,
            nro_matricula: datos.nroMatricula,
            escribania_nombre: datos.escribaniaNombre
          });
          
          setUsuario(prev => prev ? ({
            ...prev,
            nombre: updatedUser.nombre_completo,
            nombre_completo: updatedUser.nombre_completo,
            nroMatricula: updatedUser.nro_matricula,
            escribaniaNombre: updatedUser.escribania_nombre
          }) : null);
          setFormPerfil(datos);
        }}
      />

      <CambiarContrasenaModal
        open={dialogCambiarContrasena}
        onOpenChange={setDialogCambiarContrasena}
      />

      <PreviewDocumentoModal
        open={dialogPreviewDocumento}
        onOpenChange={setDialogPreviewDocumento}
        documentoPreview={documentoPreview}
        onDownload={descargarDocumento}
        formatearFecha={formatearFecha}
      />

      <NuevoWorkspaceModal
        open={dialogNuevoWorkspace}
        onOpenChange={setDialogNuevoWorkspace}
        onSuccess={(nuevoWorkspace) => {
          setWorkspaces([...workspaces, nuevoWorkspace]);
          setWorkspaceActual(nuevoWorkspace);
        }}
      />

      <NuevoTramiteModal
        open={dialogNuevoTramite}
        onOpenChange={setDialogNuevoTramite}
        workspaceId={workspaceActual?.id ? Number(workspaceActual.id) : undefined}
        clienteId={clienteActual?.id}
        onSuccess={(nuevoTramite) => {
          const mapped: Tramite = {
            id: nuevoTramite.id,
            tenant_id: DEFAULT_TENANT_ID,
            nombre: nuevoTramite.nombre,
            estado: nuevoTramite.estado as any,
            tipo: nuevoTramite.tipo,
            workspaceId: nuevoTramite.workspace_id.toString(),
            clienteId: nuevoTramite.cliente_id,
            fechaCreacion: new Date(nuevoTramite.fecha_creacion),
            fechaActualizacion: new Date(nuevoTramite.fecha_actualizacion)
          };
          setTramites(prev => [...prev, mapped]);
          setTramiteActual(mapped);
          setActiveTab('asistente');
        }}
        initialData={formTramite}
      />

      {/* Modales Fase 4 */}
      <NuevoClienteModal 
        isOpen={isNuevoClienteOpen} 
        onClose={() => setIsNuevoClienteOpen(false)}
        workspaceId={Number(workspaceActual?.id)}
        cliente={clienteEditandoId ? clientes.find(c => c.id === clienteEditandoId) : undefined}
        onSuccess={(nuevoCliente: any) => {
          setClientes(prev => {
            const exists = prev.find(c => c.id === nuevoCliente.id)
            if (exists) return prev.map(c => c.id === nuevoCliente.id ? nuevoCliente : c)
            return [nuevoCliente, ...prev]
          })
          setClienteActual(nuevoCliente)
        }}
      />

      {workspaceActual && (
        <GlobalChatPanel 
          isOpen={globalChatOpen}
          onClose={() => setGlobalChatOpen(false)}
          sessionId={activeGlobalChatId}
          sessionTitle={activeGlobalChatTitle}
          workspaceId={workspaceActual.id}
        />
      )}
      <style jsx global>{`
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
        
        .animate-premium-in {
          animation: premium-in 0.6s cubic-bezier(0.16, 1, 0.3, 1);
        }

        @keyframes premium-in {
          from { opacity: 0; transform: translateY(10px) scale(0.98); }
          to { opacity: 1; transform: translateY(0) scale(1); }
        }

        .prose-notarial p {
          margin-bottom: 1.25rem;
          line-height: 1.8;
          text-align: justify;
          color: hsl(var(--foreground));
        }
        
        .prose-notarial strong {
          color: hsl(var(--foreground));
          font-weight: 700;
          letter-spacing: -0.01em;
        }

        .prose-notarial ul, .prose-notarial ol {
          margin-bottom: 1.5rem;
          padding-left: 1.5rem;
        }

        .prose-notarial li {
          margin-bottom: 0.5rem;
          line-height: 1.6;
        }

        .prose-notarial h1, .prose-notarial h2, .prose-notarial h3 {
          color: hsl(var(--primary));
          margin-top: 2rem;
          margin-bottom: 1rem;
          font-weight: 700;
        }

        .glass-premium {
          background: rgba(var(--card), 0.7);
          backdrop-filter: blur(12px);
          border: 1px solid rgba(var(--border), 0.5);
          box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.05);
        }

        .dark .glass-premium {
          background: rgba(15, 23, 42, 0.6);
          border: 1px solid rgba(255, 255, 255, 0.05);
        }
      `}</style>

      {/* Modal Editor de Documentos */}
      <DocumentoEditorModal
        archivo={documentoEditorArchivo}
        open={documentoEditorOpen}
        onClose={() => setDocumentoEditorOpen(false)}
      />
    </div>
  )
}
