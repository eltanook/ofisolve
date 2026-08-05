import React, { useState } from "react";
import { Search, UserPlus, ChevronDown, ChevronRight, UserIcon, Folder, FolderPlus, History, ChevronUp, Lock, Scale, FileText, BookOpen, Brain, Calendar, DollarSign, Calculator, StickyNote, ShieldAlert, Pencil, LayoutGrid, Users, X } from "lucide-react";
import Link from "next/link";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { ofisolveApi } from "@/lib/api";
import { toast } from "sonner";
import { Tramite, ClienteResponse, Workspace, Usuario, DocumentoFuente } from "@/lib/types";

interface SidebarProps {
  clientes: ClienteResponse[];
  tramites: Tramite[];
  workspaceActual: Workspace | null;
  clienteActual: ClienteResponse | null;
  setClienteActual: (cliente: ClienteResponse | null) => void;
  tramiteActual: Tramite | null;
  setTramiteActual: (tramite: Tramite | null) => void;
  documentoActual: DocumentoFuente | null;
  setDocumentoActual: (documento: DocumentoFuente | null) => void;
  setClienteEditandoId: (id: number | null) => void;
  setIsNuevoClienteOpen: (open: boolean) => void;
  setIsNuevoTramiteOpen: (open: boolean) => void;
  onMoverTramite?: (tramiteId: number, nuevoClienteId: number) => void;
  onMoverDocumento?: (documentoId: number, nuevoTramiteId: number) => void;
  archivosPorTramite: Record<number, any[]>;
  setArchivosPorTramite: React.Dispatch<React.SetStateAction<Record<number, any[]>>>;
  usuario: Usuario | null;
  onAbrirDocumento?: (archivo: any) => void;
  onOpenGlobalChat?: (sessionId: number, sessionTitle: string) => void;
}

export function Sidebar({
  clientes,
  tramites,
  workspaceActual,
  clienteActual,
  setClienteActual,
  tramiteActual,
  setTramiteActual,
  documentoActual,
  setDocumentoActual,
  setClienteEditandoId,
  setIsNuevoClienteOpen,
  setIsNuevoTramiteOpen,
  onMoverTramite,
  onMoverDocumento,
  archivosPorTramite,
  setArchivosPorTramite,
  usuario,
  onAbrirDocumento,
  onOpenGlobalChat,
}: SidebarProps) {
  const [showArchived, setShowArchived] = useState(false);
  const [busqueda, setBusqueda] = useState("");
  const [chatSessions, setChatSessions] = useState<any[]>([]);
  const [isChatsExpanded, setIsChatsExpanded] = React.useState(true);
  const [expandedClients, setExpandedClients] = React.useState<number[]>([]);
  const [expandedTramites, setExpandedTramites] = React.useState<number[]>([]);
  const [isHerramientasExpanded, setIsHerramientasExpanded] = useState(true);
  const [isClientesExpanded, setIsClientesExpanded] = useState(true);

  React.useEffect(() => {
    if (workspaceActual?.id) {
      ofisolveApi.obtenerChatSessions(workspaceActual.id).then(setChatSessions).catch(() => {});
    }
  }, [workspaceActual?.id]);

  const handleCrearChat = async () => {
    if (!workspaceActual?.id) return;
    try {
      const title = `Consulta - ${new Date().toLocaleDateString()}`;
      const newSession = await ofisolveApi.crearChatSession(workspaceActual.id, title);
      setChatSessions([newSession, ...chatSessions]);
      if (onOpenGlobalChat) onOpenGlobalChat(newSession.id, newSession.titulo);
    } catch (e) {
      toast.error("Error creando sesión de chat");
    }
  };

  const handleEliminarChat = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    if (!workspaceActual?.id) return;
    try {
      await ofisolveApi.eliminarChatSession(workspaceActual.id, id);
      setChatSessions(chatSessions.filter(s => s.id !== id));
      toast.success("Chat eliminado");
    } catch (e) {
      toast.error("Error eliminando chat");
    }
  };

  // Filtrar clientes y trámites basado en el texto de búsqueda
  const clientesFiltrados = busqueda.trim()
    ? clientes.filter(c =>
        c.nombre_completo.toLowerCase().includes(busqueda.toLowerCase()) ||
        c.dni?.includes(busqueda) ||
        c.cuit?.includes(busqueda)
      )
    : clientes;

  const tramitesSinCliente = tramites.filter(t =>
    t.workspaceId == workspaceActual?.id &&
    !t.clienteId &&
    t.estado !== 'archivado' &&
    (busqueda.trim() ? t.nombre.toLowerCase().includes(busqueda.toLowerCase()) : true)
  );

  return (
    <aside className="flex h-full flex-col border-r border-border bg-sidebar overflow-x-hidden">
      {/* Buscador de Clientes Removido (Ahora es global en el Navbar) */}

      {/* Módulos Principales ERP */}
      <div className="shrink-0 px-2 py-2 border-b border-border">
        <div 
          className="flex items-center justify-between px-2 py-1.5 cursor-pointer rounded-lg hover:bg-accent group transition-colors"
          onClick={() => setIsHerramientasExpanded(!isHerramientasExpanded)}
        >
          <div className="flex items-center gap-2">
            <LayoutGrid className="h-4 w-4 text-muted-foreground" />
            <span className="text-xs font-bold uppercase tracking-widest text-muted-foreground group-hover:text-foreground">
              Herramientas
            </span>
          </div>
          {isHerramientasExpanded ? <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" /> : <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />}
        </div>
        
        {isHerramientasExpanded && (
          <div className="mt-1 flex flex-col gap-0.5">
            <Link href={`/?workspaceId=${workspaceActual?.id || ''}`} className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors">
              <Folder className="h-3.5 w-3.5" />
              Escritorio
            </Link>
            <Link href={`/agenda?workspaceId=${workspaceActual?.id || ''}`} className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors">
              <Calendar className="h-3.5 w-3.5" />
              Agenda y Vencimientos
            </Link>
            <Link href={`/finanzas?workspaceId=${workspaceActual?.id || ''}`} className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors">
              <DollarSign className="h-3.5 w-3.5" />
              Finanzas y Caja
            </Link>
            <Link href={`/presupuestos?workspaceId=${workspaceActual?.id || ''}`} className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors">
              <Calculator className="h-3.5 w-3.5" />
              Presupuestador
            </Link>
            <Link href={`/notas?workspaceId=${workspaceActual?.id || ''}`} className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors">
              <StickyNote className="h-3.5 w-3.5" />
              Muro de Notas
            </Link>
            <Link href={`/plantillas?workspaceId=${workspaceActual?.id || ''}`} className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors">
              <FileText className="h-3.5 w-3.5" />
              Biblioteca de Modelos
            </Link>
            <Link href={`/uif?workspaceId=${workspaceActual?.id || ''}`} className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium text-muted-foreground hover:bg-accent hover:text-foreground transition-colors">
              <ShieldAlert className="h-3.5 w-3.5" />
              Panel UIF
            </Link>
          </div>
        )}
      </div>

      {/* CHATS GLOBALES (IA) */}
      <div className="shrink-0 px-2 py-2 border-b border-border">
        <div 
          className="flex items-center justify-between px-2 py-1.5 cursor-pointer rounded-lg hover:bg-accent group transition-colors"
          onClick={() => setIsChatsExpanded(!isChatsExpanded)}
        >
          <div className="flex items-center gap-2">
            <Brain className="h-4 w-4 text-muted-foreground" />
            <span className="text-xs font-bold uppercase tracking-widest text-muted-foreground group-hover:text-foreground">
              Agente CRM (IA)
            </span>
          </div>
          {isChatsExpanded ? <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" /> : <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />}
        </div>
        
        {isChatsExpanded && (
          <div className="mt-1 flex flex-col gap-0.5">
            <Button 
              variant="ghost" 
              size="sm" 
              className="w-full justify-start h-8 text-xs text-muted-foreground hover:text-foreground"
              onClick={handleCrearChat}
            >
              <UserPlus className="mr-2 h-3.5 w-3.5" />
              Nueva Consulta...
            </Button>
            
            <div className="max-h-[150px] overflow-y-auto pr-1">
              {chatSessions.map((chat) => (
                <div 
                  key={chat.id}
                  onClick={() => onOpenGlobalChat && onOpenGlobalChat(chat.id, chat.titulo)}
                  className="flex items-center justify-between px-2 py-1.5 rounded-md hover:bg-accent cursor-pointer group text-xs text-muted-foreground hover:text-foreground"
                >
                  <span className="truncate pr-2 flex-1">{chat.titulo}</span>
                  <button 
                    onClick={(e) => handleEliminarChat(e, chat.id)}
                    className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive p-0.5 rounded ds-transition"
                    title="Eliminar chat"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Clientes y Carpetas */}
      <div className={cn("shrink-0 px-2 py-2 transition-colors", !isClientesExpanded && "border-b border-border")}>
        <div 
          className="flex items-center justify-between px-2 py-1.5 cursor-pointer rounded-lg hover:bg-accent group transition-colors"
          onClick={() => setIsClientesExpanded(!isClientesExpanded)}
        >
          <div className="flex items-center gap-2">
            <Users className="h-4 w-4 text-muted-foreground" />
            <span className="text-xs font-bold uppercase tracking-widest text-muted-foreground group-hover:text-foreground">
              Clientes y Carpetas
            </span>
          </div>
          <div className="flex items-center gap-1">
            <Button 
              variant="ghost" 
              size="icon" 
              className="h-6 w-6 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-foreground"
              onClick={(e) => { e.stopPropagation(); setIsNuevoTramiteOpen(true); }}
              title="Crear nueva carpeta (trámite)"
            >
              <FolderPlus className="h-3.5 w-3.5" />
            </Button>
            <Button 
              variant="ghost" 
              size="icon" 
              className="h-6 w-6 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-foreground"
              onClick={(e) => { e.stopPropagation(); setIsNuevoClienteOpen(true); }}
              title="Agregar cliente"
            >
              <UserPlus className="h-3.5 w-3.5" />
            </Button>
            {isClientesExpanded ? <ChevronDown className="h-3.5 w-3.5 text-muted-foreground ml-1" /> : <ChevronRight className="h-3.5 w-3.5 text-muted-foreground ml-1" />}
          </div>
        </div>
      </div>

      {/* Explorador Jerárquico */}
      {isClientesExpanded && (
      <ScrollArea className="flex-1 px-2">
        <div className="flex flex-col gap-1 py-2">
          {clientesFiltrados.length === 0 && tramitesSinCliente.length === 0 && (
            <div className="flex flex-col items-center justify-center p-4 text-center mt-4">
              <Folder className="h-8 w-8 text-muted-foreground/30 mb-2" />
              <p className="text-xs text-muted-foreground">{busqueda ? "Sin resultados" : "No hay carpetas"}</p>
              {!busqueda && (
                <Button 
                  variant="outline" 
                  size="sm" 
                  className="mt-3 text-[10px] h-7"
                  onClick={() => setIsNuevoClienteOpen(true)}
                >
                  Crear Cliente
                </Button>
              )}
            </div>
          )}
          
          {clientesFiltrados.map((cliente) => {
            const isExpanded = expandedClients.includes(cliente.id);
            const isSelected = clienteActual?.id === cliente.id;
            
            return (
              <div 
                key={cliente.id} 
                className="flex flex-col gap-1"
                onDragOver={(e) => {
                  e.preventDefault();
                  // Visual feedback can be added here
                }}
                onDrop={(e) => {
                  e.preventDefault();
                  const tramiteId = e.dataTransfer.getData("tramiteId");
                  if (tramiteId && onMoverTramite) {
                    if (window.confirm(`¿Estás seguro que deseas mover esta carpeta al cliente ${cliente.nombre_completo}?`)) {
                      onMoverTramite(Number(tramiteId), cliente.id);
                    }
                  }
                }}
              >
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => {
                      setExpandedClients(prev => 
                        isExpanded ? prev.filter(id => id !== cliente.id) : [...prev, cliente.id]
                      );
                      setClienteActual(cliente);
                    }}
                    className={cn(
                      "flex-1 flex items-center gap-2 rounded-xl px-3 py-2.5 text-left transition-all",
                      isSelected 
                        ? "bg-primary/10 text-primary" 
                        : "hover:bg-accent/50 text-foreground"
                    )}
                  >
                  <div className={cn(
                    "h-8 w-8 shrink-0 flex items-center justify-center rounded-lg",
                    isSelected ? "bg-primary/20" : "bg-muted"
                  )}>
                    <UserIcon className="h-4 w-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="truncate text-sm font-semibold">{cliente.nombre_completo}</p>
                    <p className="truncate text-[10px] opacity-70">DNI {cliente.dni}</p>
                  </div>
                  {isExpanded ? (
                    <ChevronDown className="h-4 w-4 shrink-0 opacity-50" />
                  ) : (
                    <ChevronRight className="h-4 w-4 shrink-0 opacity-50" />
                  )}
                  </button>
                  {isExpanded && (
                    <Button 
                      variant="ghost" 
                      size="icon" 
                      className="h-8 w-8 text-muted-foreground hover:text-primary shrink-0 rounded-lg"
                      title="Editar Cliente"
                      onClick={(e) => {
                        e.stopPropagation();
                        // Al hacer clic, nos aseguramos que este es el cliente que se va a editar
                        setClienteEditandoId(cliente.id); 
                        setIsNuevoClienteOpen(true);
                      }}
                    >
                      <Pencil className="h-4 w-4" />
                      <span className="sr-only">Editar</span>
                    </Button>
                  )}
                </div>

                {/* Carpetas (Trámites) del cliente */}
                {isExpanded && (
                  <div className="ml-8 mt-1 flex flex-col gap-1 border-l border-border pl-2 animate-in slide-in-from-left-2 duration-200">
                    {tramites.filter(t => t.workspaceId == workspaceActual?.id && t.estado !== 'archivado' && t.clienteId == cliente.id).map((tramite) => {
                      const isTramiteSelected = tramiteActual?.id === tramite.id;
                      const archivos = archivosPorTramite[tramite.id] || [];
                      
                      return (
                        <div key={tramite.id} className="flex flex-col gap-0.5">
                          <button
                            draggable
                            onDragStart={(e) => {
                              e.dataTransfer.setData("tramiteId", tramite.id.toString());
                            }}
                            onDragOver={(e) => e.preventDefault()}
                            onDrop={async (e) => {
                              e.preventDefault();
                              const docId = e.dataTransfer.getData("documentoId");
                              if (docId && onMoverDocumento) {
                                if (window.confirm(`¿Estás seguro que deseas mover este archivo a la carpeta ${tramite.nombre}?`)) {
                                  onMoverDocumento(Number(docId), tramite.id);
                                }
                                return;
                              }
                              
                              if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                                e.stopPropagation();
                                const file = e.dataTransfer.files[0];
                                if (workspaceActual) {
                                  try {
                                    toast.info(`Subiendo ${file.name}...`);
                                    await ofisolveApi.subirDocumento(workspaceActual.id, file, tramite.id);
                                    toast.success(`${file.name} subido exitosamente`);
                                    
                                    ofisolveApi.obtenerArchivosTramite(tramite.id)
                                      .then(docs => setArchivosPorTramite(prev => ({ ...prev, [tramite.id]: docs })))
                                      .catch(err => console.error(err));
                                  } catch (error: any) {
                                    toast.error(`Error al subir archivo: ${error.message}`);
                                  }
                                }
                              }
                            }}
                            onClick={() => {
                              setTramiteActual(tramite);
                              setExpandedTramites(prev => prev.includes(tramite.id) ? prev.filter(id => id !== tramite.id) : [...prev, tramite.id]);
                              // Cargar archivos al hacer click
                              if (!archivosPorTramite[tramite.id]) {
                                ofisolveApi.obtenerArchivosTramite(tramite.id)
                                  .then(docs => setArchivosPorTramite(prev => ({ ...prev, [tramite.id]: docs })))
                                  .catch(err => console.error(err));
                              }
                            }}
                            className={cn(
                              "flex w-full items-center justify-between rounded-lg px-3 py-1.5 text-left text-xs transition-all group/item",
                              isTramiteSelected
                                ? "bg-primary/10 text-primary font-medium"
                                : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
                            )}
                          >
                            <div className="flex items-center gap-2 min-w-0">
                              <Folder className="h-3.5 w-3.5 shrink-0 opacity-70" />
                              <span className="truncate">{tramite.nombre}</span>
                            </div>
                          </button>

                          {/* Archivos del trámite */}
                          {expandedTramites.includes(tramite.id) && archivos.length > 0 && (
                            <div className="ml-4 mt-1 flex flex-col gap-0.5 border-l border-primary/20 pl-2 animate-in fade-in duration-200">
                              {archivos.map(archivo => (
                                <button
                                  key={archivo.id}
                                  draggable
                                  onDragStart={(e) => {
                                    e.stopPropagation();
                                    e.dataTransfer.setData("documentoId", archivo.id.toString());
                                    e.dataTransfer.setData("documentoMeta", JSON.stringify({ id: archivo.id, nombre: archivo.nombre, tramiteId: tramite.id }));
                                  }}
                                  onClick={async () => {
                                    setDocumentoActual(archivo);
                                    if (onAbrirDocumento) {
                                      onAbrirDocumento(archivo);
                                    } else {
                                      try {
                                        const doc = await ofisolveApi.obtenerContenidoDocumento(archivo.id);
                                        if (doc) {
                                          toast.success(`Seleccionado ${archivo.nombre}`);
                                        }
                                      } catch(e) {
                                        toast.error("Error al cargar documento");
                                      }
                                    }
                                  }}
                                  className={cn(
                                    "flex w-full items-center gap-2 rounded-md px-2 py-1 text-[11px] transition-all",
                                    documentoActual?.id === archivo.id
                                      ? "bg-primary/20 text-primary font-medium"
                                      : "text-muted-foreground hover:bg-accent/30 hover:text-foreground"
                                  )}
                                >
                                  <FileText className="h-3 w-3 shrink-0 opacity-50" />
                                  <span className="truncate">{archivo.nombre}</span>
                                </button>
                              ))}
                            </div>
                          )}
                        </div>
                      );
                    })}
                    
                    {tramites.filter(t => t.workspaceId == workspaceActual?.id && t.estado !== 'archivado' && t.clienteId == cliente.id).length === 0 && (
                      <div className="px-3 py-2 text-[10px] text-muted-foreground/60 italic">
                        No hay carpetas
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
          
          {tramitesSinCliente.length > 0 && (
            <div className="mt-4">
              <div className="px-3 py-1 text-[9px] font-bold uppercase tracking-wider text-muted-foreground/50">
                Otras carpetas
              </div>
              <div className="flex flex-col gap-0.5">
                {tramitesSinCliente.map((tramite) => {
                  const isTramiteSelected = tramiteActual?.id === tramite.id;
                  const archivos = archivosPorTramite[tramite.id] || [];
                  return (
                    <div key={tramite.id} className="flex flex-col gap-0.5">
                      <button
                        draggable
                        onDragStart={(e) => {
                          e.dataTransfer.setData("tramiteId", tramite.id.toString());
                        }}
                        onDragOver={(e) => e.preventDefault()}
                        onDrop={async (e) => {
                          e.preventDefault();
                          const docId = e.dataTransfer.getData("documentoId");
                          if (docId && onMoverDocumento) {
                            if (window.confirm(`¿Estás seguro que deseas mover este archivo a la carpeta ${tramite.nombre}?`)) {
                              onMoverDocumento(Number(docId), tramite.id);
                            }
                            return;
                          }
                          
                          if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                            e.stopPropagation();
                            const file = e.dataTransfer.files[0];
                            if (workspaceActual) {
                              try {
                                toast.info(`Subiendo ${file.name}...`);
                                await ofisolveApi.subirDocumento(workspaceActual.id, file, tramite.id);
                                toast.success(`${file.name} subido exitosamente`);
                                
                                ofisolveApi.obtenerArchivosTramite(tramite.id)
                                  .then(docs => setArchivosPorTramite(prev => ({ ...prev, [tramite.id]: docs })))
                                  .catch(err => console.error(err));
                              } catch (error: any) {
                                toast.error(`Error al subir archivo: ${error.message}`);
                              }
                            }
                          }
                        }}
                        onClick={() => {
                          setTramiteActual(tramite);
                          // Cargar archivos al hacer click
                          if (!archivosPorTramite[tramite.id]) {
                            ofisolveApi.obtenerArchivosTramite(tramite.id)
                              .then(docs => setArchivosPorTramite(prev => ({ ...prev, [tramite.id]: docs })))
                              .catch(err => console.error(err));
                          }
                        }}
                        className={cn(
                          "flex w-full items-center gap-2 rounded-lg px-3 py-1.5 text-left text-xs transition-all",
                          isTramiteSelected
                            ? "bg-primary/10 text-primary font-medium"
                            : "text-muted-foreground hover:bg-accent/30 hover:text-foreground"
                        )}
                      >
                        <Folder className="h-3.5 w-3.5 shrink-0" />
                        <span className="truncate flex-1">{tramite.nombre}</span>
                        {archivos.length > 0 && (
                          <span className={cn(
                            "text-[9px] px-1 rounded-full font-bold",
                            isTramiteSelected ? "bg-primary/20 text-primary" : "bg-muted text-muted-foreground"
                          )}>{archivos.length}</span>
                        )}
                      </button>
                      {/* Archivos del trámite sin cliente */}
                      {isTramiteSelected && archivos.length > 0 && (
                        <div className="ml-4 mt-0.5 flex flex-col gap-0.5 border-l border-primary/20 pl-2 animate-in fade-in duration-200">
                          {archivos.map(archivo => (
                            <button
                              key={archivo.id}
                              onClick={async () => {
                              if (onAbrirDocumento) {
                                onAbrirDocumento(archivo);
                              } else {
                                try {
                                  await ofisolveApi.obtenerContenidoDocumento(archivo.id);
                                  toast.success(`Cargando ${archivo.nombre}`);
                                } catch(e) {
                                  toast.error("Error al cargar documento");
                                }
                              }
                            }}
                              className="flex w-full items-center gap-2 rounded-md px-2 py-1 text-[11px] text-muted-foreground hover:bg-accent/30 hover:text-foreground transition-all"
                            >
                              <FileText className="h-3 w-3 shrink-0 opacity-50" />
                              <span className="truncate">{archivo.nombre}</span>
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
        
        {/* SECCION DE ARCHIVADOS */}
        <div className="shrink-0 border-t border-border mt-2 pt-1 bg-muted/5">
          <button
            onClick={() => setShowArchived(!showArchived)}
            className="flex w-full items-center justify-between px-3 py-2 text-[10px] font-bold uppercase tracking-widest text-muted-foreground hover:bg-muted/30 transition-colors rounded-lg"
          >
            <div className="flex items-center gap-2">
              <History className="h-3.5 w-3.5" />
              Expedientes Archivados
            </div>
            {showArchived ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
          </button>
          
          {showArchived && (
            <div className="mt-1 flex flex-col gap-0.5 animate-in slide-in-from-top-1">
              {clientes.filter(c => tramites.some(t => t.clienteId === c.id && t.estado === 'archivado')).map(cliente => (
                <div key={`arch-${cliente.id}`} className="mb-1">
                  <div className="px-3 py-1 text-[9px] font-bold text-muted-foreground/50 uppercase tracking-tighter">{cliente.nombre_completo}</div>
                  <div className="ml-2 flex flex-col gap-0.5 border-l border-border pl-2">
                    {tramites.filter(t => t.clienteId === cliente.id && t.estado === 'archivado').map(t => (
                      <button
                        key={t.id}
                        onClick={() => setTramiteActual(t)}
                        className={cn(
                          "flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-[11px] text-muted-foreground hover:bg-accent/50 transition-colors",
                          tramiteActual?.id === t.id && "bg-accent text-foreground font-medium"
                        )}
                      >
                        <Lock className="h-3 w-3 opacity-50" />
                        <span className="truncate">{t.nombre}</span>
                      </button>
                    ))}
                  </div>
                </div>
              ))}
              {tramites.filter(t => !t.clienteId && t.estado === 'archivado').length > 0 && (
                  <div className="mt-1">
                    <div className="px-3 py-1 text-[9px] font-bold text-muted-foreground/50 uppercase tracking-tighter">Sin Cliente</div>
                    <div className="ml-2 flex flex-col gap-0.5 border-l border-border pl-2">
                        {tramites.filter(t => !t.clienteId && t.estado === 'archivado').map(t => (
                          <button
                            key={t.id}
                            onClick={() => setTramiteActual(t)}
                            className={cn(
                              "flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-[11px] text-muted-foreground hover:bg-accent/50",
                              tramiteActual?.id === t.id && "bg-accent text-foreground font-medium"
                            )}
                          >
                            <Lock className="h-3 w-3 opacity-50" />
                            <span className="truncate">{t.nombre}</span>
                          </button>
                        ))}
                    </div>
                  </div>
              )}
              {tramites.filter(t => t.estado === 'archivado').length === 0 && (
                <div className="py-2 text-center text-[10px] text-muted-foreground italic">
                  No hay expedientes archivados
                </div>
              )}
            </div>
          )}
        </div>
      </ScrollArea>
      )}


      {/* Info Escribanía Footer */}
      <div className="mt-auto border-t border-border p-4 bg-accent/20">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-primary flex items-center justify-center shadow-lg shadow-primary/20">
            <Scale className="h-5 w-5 text-primary-foreground" />
          </div>
          <div className="min-w-0">
            <p className="text-xs font-bold truncate">{usuario?.escribaniaNombre}</p>
            <p className="text-[10px] text-muted-foreground truncate">Registro {usuario?.nroMatricula}</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
