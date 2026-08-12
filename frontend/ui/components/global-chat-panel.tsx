"use client"

import * as React from "react"
import { useState, useRef, useEffect, useCallback } from "react"
import { 
  Sheet, 
  SheetContent, 
  SheetHeader, 
  SheetTitle 
} from "@/components/ui/sheet"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Send, Loader2, Brain, Bot, User, Sparkles, Maximize, Minimize, Check, X, Copy, Download, StickyNote } from "lucide-react"
import { ofisolveApi } from "@/lib/api"
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { fetchEventSource } from '@microsoft/fetch-event-source'
import { cn } from "@/lib/utils"
import { toast } from "sonner"

interface GlobalChatPanelProps {
  isOpen: boolean
  onClose: () => void
  sessionId: number | null
  sessionTitle: string
  workspaceId: number
}

interface Message {
  role: "user" | "assistant"
  contenido: string
  id?: number
}

export function GlobalChatPanel({ isOpen, onClose, sessionId, sessionTitle, workspaceId }: GlobalChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [isStreaming, setIsStreaming] = useState(false)
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [agentSteps, setAgentSteps] = useState<{msg: string, status: 'loading' | 'done' | 'error'}[]>([])
  const [fuentesAdjuntas, setFuentesAdjuntas] = useState<{id: number, nombre: string}[]>([])
  const [isDragOver, setIsDragOver] = useState(false)
  const [isFullScreen, setIsFullScreen] = useState(false)
  const [panelWidth, setPanelWidth] = useState(800)
  const isResizing = useRef(false)
  
  const [showSlashMenu, setShowSlashMenu] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  
  const iniciarResize = (e: React.MouseEvent) => {
    e.preventDefault();
    isResizing.current = true;
    document.addEventListener("mousemove", manejarResize);
    document.addEventListener("mouseup", detenerResize);
    document.body.style.cursor = 'col-resize';
  };

  const manejarResize = useCallback((e: MouseEvent) => {
    if (!isResizing.current) return;
    const newWidth = window.innerWidth - e.clientX;
    if (newWidth > 400 && newWidth < window.innerWidth - 100) {
      setPanelWidth(newWidth);
    }
  }, []);

  const detenerResize = useCallback(() => {
    isResizing.current = false;
    document.removeEventListener("mousemove", manejarResize);
    document.removeEventListener("mouseup", detenerResize);
    document.body.style.cursor = 'default';
  }, [manejarResize]);

  useEffect(() => {
    return () => {
      document.removeEventListener("mousemove", manejarResize);
      document.removeEventListener("mouseup", detenerResize);
      document.body.style.cursor = 'default';
    };
  }, [manejarResize, detenerResize]);

  useEffect(() => {
    if (isOpen && sessionId) {
      cargarHistorial()
    } else {
      setMessages([])
    }
  }, [isOpen, sessionId])

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, agentSteps])

  const cargarHistorial = async () => {
    if (!sessionId) return
    setLoadingHistory(true)
    try {
      const hist = await ofisolveApi.obtenerMensajesChatSession(sessionId)
      setMessages(hist.map((m: any) => ({ role: m.role, contenido: m.contenido, id: m.id })))
    } catch (e) {
      console.error("Error al cargar historial", e)
    } finally {
      setLoadingHistory(false)
    }
  }

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    if (!input.trim() || isStreaming) return
    const msg = input.trim()
    setInput("")
    enviarMensaje(msg, fuentesAdjuntas.map(f => f.id))
    setFuentesAdjuntas([])
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const enviarMensaje = async (userMsg: string, fuentesIds?: number[]) => {
    if (!sessionId) return

    setMessages(prev => [...prev, { role: "user", contenido: userMsg }])
    
    if (!userMsg) return

    setIsStreaming(true)
    setAgentSteps([])
    ofisolveApi.guardarMensajeChatSession(sessionId, "user", userMsg).catch(console.error)
    
    let aiResponse = ""
    setMessages(prev => [...prev, { role: "assistant", contenido: "" }])

    const token = typeof window !== 'undefined' ? localStorage.getItem('ofisolve-token') : null
    const ctrl = new AbortController()

    try {
      await fetchEventSource(`http://127.0.0.1:8080/api/v1/chat/chat-sessions/${sessionId}/stream`, {
        method: "POST",
        signal: ctrl.signal,
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          mensaje: userMsg,
          history: messages,
          ...(fuentesIds && fuentesIds.length > 0 ? { fuentes_ids: fuentesIds } : {})
        }),
        onmessage(event) {
          const data = JSON.parse(event.data)
          if (data.event === "estado") {
            setAgentSteps(prev => {
              const newSteps = [...prev]
              if (data.mensaje.startsWith('Ejecutando:')) {
                newSteps.push({ msg: data.mensaje, status: 'loading' })
              } else if (data.mensaje.startsWith('Finalizado:')) {
                let found = false
                const toolName = data.mensaje.replace('Finalizado: ', '').trim()
                for (let i = newSteps.length - 1; i >= 0; i--) {
                  if (newSteps[i].status === 'loading' && newSteps[i].msg.includes(toolName)) {
                    newSteps[i] = { msg: data.mensaje, status: 'done' }
                    found = true
                    break
                  }
                }
                if (!found) newSteps.push({ msg: data.mensaje, status: 'done' })
              } else {
                newSteps.push({ msg: data.mensaje, status: 'error' })
              }
              return newSteps
            })
          } else if (data.event === "token") {
            aiResponse += data.texto
            setMessages(prev => {
              const newMsgs = [...prev]
              newMsgs[newMsgs.length - 1].contenido = aiResponse
              return newMsgs
            })
          } else if (data.event === "finalizado") {
            ofisolveApi.guardarMensajeChatSession(sessionId, "assistant", aiResponse).catch(console.error)
            setIsStreaming(false)
            ctrl.abort()
          }
        },
        onclose() {
          // Si finalizó naturalmente, ya guardamos y abortamos en 'finalizado'
        },
        onerror(err) {
          if (err.name === 'AbortError') {
             return; // Ignore abort errors
          }
          console.error("Error streaming SSE:", err)
          setIsStreaming(false)
          setAgentSteps(prev => [...prev, { msg: "Error en la conexión con la IA", status: 'error' }])
          throw err
        }
      })
    } catch (err) {
      setIsStreaming(false)
      setAgentSteps(prev => [...prev, { msg: "Fallo la respuesta", status: 'error' }])
    }
  }

  return (
    <Sheet open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <SheetContent 
        style={{ maxWidth: '100vw', width: isFullScreen ? '100vw' : `${panelWidth}px` }}
        className={cn(
          "flex flex-col p-0 border-l border-border bg-background transition-none ease-in-out [&>button.absolute]:hidden"
        )} 
        side="right"
      >
        {!isFullScreen && (
          <div 
            onMouseDown={iniciarResize}
            className="absolute -left-1 top-0 bottom-0 w-3 cursor-col-resize hover:bg-primary/20 hover:border-l-2 hover:border-primary active:bg-primary/30 z-50 transition-colors"
          />
        )}
        <SheetHeader className="p-4 border-b shrink-0 flex flex-row items-center gap-3">
          <div className="bg-primary/10 p-2 rounded-full">
            <Brain className="h-5 w-5 text-primary" />
          </div>
          <div className="flex-1">
            <SheetTitle className="text-lg">{sessionTitle || "Gestor de Clientes IA"}</SheetTitle>
            <p className="text-xs text-muted-foreground">Acceso global a toda la base de datos de la escribanía</p>
          </div>
          <Button 
            variant="ghost" 
            size="icon" 
            className="rounded-full text-muted-foreground hover:text-foreground"
            onClick={() => setIsFullScreen(!isFullScreen)}
            title={isFullScreen ? "Minimizar" : "Pantalla Completa"}
          >
            {isFullScreen ? <Minimize className="h-4 w-4" /> : <Maximize className="h-4 w-4" />}
          </Button>
          <button 
            onClick={onClose}
            className="h-9 w-9 inline-flex items-center justify-center rounded-full text-muted-foreground hover:text-foreground hover:bg-accent/50 transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </SheetHeader>

        <div className="flex-1 min-h-0 overflow-y-auto p-4 flex flex-col relative" ref={scrollRef as any}>
          {loadingHistory ? (
            <div className="flex justify-center items-center h-full text-muted-foreground text-sm gap-2">
              <Loader2 className="h-4 w-4 animate-spin" /> Cargando historial...
            </div>
          ) : messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground text-center space-y-5 p-8">
              <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center shadow-inner">
                <Sparkles className="h-8 w-8 text-primary" />
              </div>
              <div className="text-sm max-w-[250px] mb-6">
                <p className="font-semibold text-foreground text-base mb-2">Asistente Global Iniciado</p>
                <p className="leading-relaxed">Pregúntame sobre cualquier cliente, o pídeme que modifique sus datos directamente en la base de datos.</p>
              </div>

              <div className="flex flex-col gap-2 mt-4 max-w-sm w-full">
                <p className="text-xs text-muted-foreground font-medium mb-1 text-center">Prueba preguntando:</p>
                {[
                  "¿Cuáles son los clientes con más deuda?",
                  "Busca el último trámite de Tomás Andal",
                  "Muestra un resumen de los expedientes archivados",
                ].map((sug, i) => (
                  <button 
                    key={i}
                    onClick={() => setInput(sug)}
                    className="text-left text-xs bg-muted/30 hover:bg-muted p-3 rounded-xl border border-border/50 text-foreground transition-colors flex items-center justify-between group"
                  >
                    <span>{sug}</span>
                    <Sparkles className="h-3 w-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-4 pb-4">
              {messages.map((m, i) => (
                <div key={i} className={`flex gap-3 ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  {m.role === 'assistant' && (
                    <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                      <Bot className="h-4 w-4 text-primary" />
                    </div>
                  )}
                  <div className={`text-sm rounded-lg px-4 py-2 max-w-[85%] ${m.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-muted text-foreground'}`}>
                    {m.role === 'assistant' ? (
                      <div className="flex flex-col gap-2 w-full">
                        <div className="prose prose-sm dark:prose-invert max-w-none">
                          <ReactMarkdown 
                            remarkPlugins={[remarkGfm]}
                            components={{
                              a: ({node, ...props}) => (
                                <a 
                                  {...props} 
                                  className="inline-flex items-center gap-1 bg-primary/10 text-primary rounded-full px-2.5 py-0.5 text-xs font-medium hover:bg-primary/20 transition-colors cursor-pointer no-underline mx-1"
                                  target="_blank"
                                >
                                  📄 {props.children}
                                </a>
                              )
                            }}
                          >
                            {m.contenido}
                          </ReactMarkdown>
                        </div>
                        {m.contenido && (
                          <div className="flex gap-2 items-center justify-end mt-1 border-t border-border/50 pt-2">
                            <Button 
                              variant="ghost" 
                              size="icon" 
                              className="h-6 w-6 text-muted-foreground hover:text-foreground hover:bg-accent/50 rounded"
                              title="Copiar texto"
                              onClick={() => {
                                navigator.clipboard.writeText(m.contenido)
                                toast.success("Texto copiado al portapapeles")
                              }}
                            >
                              <Copy className="h-3 w-3" />
                            </Button>
                            <Button 
                              variant="ghost" 
                              size="icon" 
                              className="h-6 w-6 text-muted-foreground hover:text-foreground hover:bg-accent/50 rounded"
                              title="Descargar TXT"
                              onClick={() => {
                                const element = document.createElement("a");
                                const file = new Blob([m.contenido], {type: 'text/plain'});
                                element.href = URL.createObjectURL(file);
                                element.download = "IA_Respuesta.txt";
                                document.body.appendChild(element); // Required for this to work in FireFox
                                element.click();
                                document.body.removeChild(element);
                              }}
                            >
                              <Download className="h-3 w-3" />
                            </Button>
                            {workspaceId && (
                              <Button 
                                variant="ghost" 
                                size="icon" 
                                className="h-6 w-6 text-muted-foreground hover:text-foreground hover:bg-accent/50 rounded"
                                title="Guardar como Nota"
                                onClick={async () => {
                                  try {
                                    await ofisolveApi.crearNota(workspaceId, {
                                      titulo: "Respuesta de IA",
                                      contenido: m.contenido,
                                      fijada: false
                                    })
                                    toast.success("Nota guardada en el Muro")
                                  } catch (error) {
                                    toast.error("Error al guardar la nota")
                                  }
                                }}
                              >
                                <StickyNote className="h-3 w-3" />
                              </Button>
                            )}
                          </div>
                        )}
                      </div>
                    ) : (
                      m.contenido
                    )}
                  </div>
                </div>
              ))}
              {agentSteps.length > 0 && isStreaming && (
                <div className="flex gap-3 justify-start">
                  <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0 shadow-sm border border-primary/20">
                    <Bot className="h-4 w-4 text-primary" />
                  </div>
                  <div className="flex flex-col gap-1.5 justify-start mt-1 border border-primary/20 bg-primary/5 rounded-lg p-3 min-w-[200px] max-w-[85%]">
                    <p className="text-[10px] uppercase font-bold text-primary tracking-wider mb-1 flex items-center gap-1">
                      <Brain className="h-3 w-3" /> Pasos del Agente
                    </p>
                    {agentSteps.map((step, idx) => (
                      <div key={idx} className="flex gap-2 items-center text-xs text-muted-foreground animate-in fade-in duration-300">
                        {step.status === 'loading' ? (
                          <Loader2 className="h-3 w-3 text-primary animate-spin shrink-0" />
                        ) : step.status === 'done' ? (
                          <Check className="h-3 w-3 text-green-500 shrink-0" />
                        ) : (
                          <X className="h-3 w-3 text-red-500 shrink-0" />
                        )}
                        <span>{step.msg}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="p-4 bg-background border-t border-border/50 shrink-0 shadow-[0_-10px_30px_-15px_rgba(0,0,0,0.1)] z-10 relative">
          <form onSubmit={handleSubmit} className="relative group">
            <div 
              className={`relative rounded-2xl border ${isDragOver ? "border-primary bg-primary/5 ring-4 ring-primary/10" : "border-input bg-muted/20"} focus-within:bg-background focus-within:ring-1 focus-within:ring-primary focus-within:border-primary transition-all shadow-sm`}
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragOver(true);
              }}
              onDragLeave={() => setIsDragOver(false)}
              onDrop={(e) => {
                e.preventDefault();
                setIsDragOver(false);
                const metaStr = e.dataTransfer.getData("documentoMeta");
                if (metaStr) {
                  try {
                    const meta = JSON.parse(metaStr);
                    if (!fuentesAdjuntas.find(f => f.id === meta.id)) {
                      setFuentesAdjuntas(prev => [...prev, { id: meta.id, nombre: meta.nombre }]);
                    }
                  } catch (err) {}
                }
              }}
            >
              {fuentesAdjuntas.length > 0 && (
                <div className="flex flex-wrap gap-1.5 pt-2 px-4 pb-1">
                  {fuentesAdjuntas.map(f => (
                    <div key={f.id} className="inline-flex items-center gap-1 bg-primary/10 text-primary rounded-full px-2 py-0.5 text-[10px]">
                      {f.nombre}
                      <button type="button" onClick={() => setFuentesAdjuntas(prev => prev.filter(x => x.id !== f.id))} className="ml-1 rounded-full hover:bg-primary/20 p-0.5">
                        <X className="h-2.5 w-2.5" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
              {showSlashMenu && (
                <div className="absolute bottom-full left-0 mb-2 w-64 bg-background border border-border rounded-xl shadow-lg overflow-hidden z-50">
                  <div className="px-3 py-2 text-xs font-semibold bg-muted/50 text-muted-foreground border-b border-border">Comandos Rápidos</div>
                  <div className="flex flex-col">
                    {[
                      { cmd: "/borrar", desc: "Limpia la conversación", action: () => { setMessages([]); setInput(""); setShowSlashMenu(false) } },
                      { cmd: "/resumir", desc: "Pide un resumen general", action: () => { setInput("Haz un resumen detallado de la información adjunta."); setShowSlashMenu(false) } },
                      { cmd: "/pendientes", desc: "Busca tareas o deudas", action: () => { setInput("¿Qué tareas pendientes o deudas existen?"); setShowSlashMenu(false) } }
                    ].map(c => (
                      <button 
                        key={c.cmd} 
                        type="button"
                        onClick={(e) => {
                          e.preventDefault();
                          c.action();
                          setTimeout(() => setInput(prev => prev), 10); // trigger re-render if needed
                        }}
                        className="text-left px-3 py-2 hover:bg-muted text-sm flex flex-col transition-colors"
                      >
                        <span className="font-semibold text-primary">{c.cmd}</span>
                        <span className="text-xs text-muted-foreground">{c.desc}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
              <Textarea
                value={input}
                onChange={(e) => {
                  const val = e.target.value
                  setInput(val)
                  if (val.endsWith('/')) {
                    setShowSlashMenu(true)
                  } else if (!val.includes('/')) {
                    setShowSlashMenu(false)
                  }
                }}
                onKeyDown={handleKeyDown}
                placeholder="Ej: Busca clientes con riesgo UIF medio y cambia su teléfono a..."
                className="min-h-[50px] max-h-[150px] w-full resize-none bg-transparent px-4 py-3 text-sm focus-visible:ring-0 focus-visible:outline-none border-0 pr-12 leading-relaxed"
                disabled={isStreaming}
                rows={1}
              />
              <Button
                type="submit"
                size="icon"
                className="absolute right-2 bottom-2 h-8 w-8 rounded-full shadow-sm transition-all hover:scale-105 active:scale-95 disabled:opacity-50 disabled:hover:scale-100"
                disabled={!input.trim() || isStreaming}
              >
                {isStreaming ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4 ml-0.5" />}
              </Button>
            </div>
            <div className="text-[10px] text-center text-muted-foreground mt-2 font-medium">
              El asistente puede acceder y modificar datos reales del sistema.
            </div>
          </form>
        </div>
      </SheetContent>
    </Sheet>
  )
}
