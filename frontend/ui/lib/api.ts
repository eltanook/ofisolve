/**
 * OFISOLVE API CLIENT (RECONSTRUCTED & ROBUST)
 * Cliente unificado para comunicación con el backend FastAPI.
 * Soporta autenticación, Workspaces, Trámites y Streaming de IA.
 */

export const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8080/api/v1';

class OfiSolveApi {
  private token: string | null = null;
  private workspaceId: number | null = null;

  constructor() {
    // Auto-initialize token from localStorage at construction time
    // so the very first API calls are already authenticated
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem("ofisolve_token") || sessionStorage.getItem("ofisolve_token");
      if (stored) {
        this.token = stored;
      }
    }
  }

  setToken(token: string) {
    this.token = token;
  }

  setWorkspace(id: number) {
    this.workspaceId = id;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${BASE_URL}${endpoint}`;
    
    // Recuperar token de localStorage si no está en memoria
    if (!this.token && typeof window !== 'undefined') {
      this.token = localStorage.getItem("ofisolve_token") || sessionStorage.getItem("ofisolve_token");
    }

    const isFormData = options.body instanceof FormData;
    const headers: any = {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
      ...(options.headers || {}),
    };

    try {
      const response = await fetch(url, { ...options, headers });

      if (response.status === 401 || response.status === 403) {
        if (typeof window !== 'undefined') {
          localStorage.removeItem("ofisolve_token");
          sessionStorage.removeItem("ofisolve_token");
          // Evitar bucle infinito si ya estamos en la página de login
          if (window.location.pathname !== '/') {
            window.location.href = '/';
          }
        }
        throw new Error("Sesión expirada o inválida. Por favor, inicie sesión nuevamente.");
      }

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: "Error desconocido" }));
        throw new Error(error.detail || "Error en la petición");
      }

      return response.json();
    } catch (error: any) {
      console.error(`API Request Error [${endpoint}]:`, error);
      throw error;
    }
  }

  // --- AUTENTICACIÓN ---
  async login(formData: FormData): Promise<any> {
    // NOTE: BASE_URL already contains /api/v1, so we must NOT repeat it
    const response = await fetch(`${BASE_URL}/auth/login`, {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Credenciales inválidas" }));
      throw new Error(error.detail || "Error en la petición");
    }
    return response.json();
  }

  async registrar(data: any): Promise<any> {
    return this.request("/auth/register", { 
      method: "POST", 
      body: JSON.stringify(data),
      headers: { "Content-Type": "application/json" }
    });
  }

  async obtenerPerfil(): Promise<any> {
    return this.request("/auth/me");
  }

  async actualizarPerfil(datos: any): Promise<any> {
    return this.request("/auth/me", {
      method: "PATCH",
      body: JSON.stringify(datos)
    });
  }

  async subirAvatar(file: File): Promise<any> {
    const formData = new FormData();
    formData.append("file", file);
    return this.request("/auth/me/avatar", {
      method: "POST",
      body: formData
    });
  }

  // --- WORKSPACES ---
  async obtenerWorkspaces(): Promise<any[]> {
    return this.request("/workspaces/");
  }

  async crearWorkspace(data: { nombre: string; descripcion?: string }): Promise<any> {
    return this.request("/workspaces/", { method: "POST", body: JSON.stringify(data) });
  }

  // --- TRAMITES ---
  async obtenerTramites(workspaceId: number): Promise<any[]> {
    return this.request(`/workspaces/${workspaceId}/tramites`);
  }

  async crearTramite(workspaceId: number, data: any): Promise<any> {
    return this.request(`/workspaces/${workspaceId}/tramites`, { method: "POST", body: JSON.stringify(data) });
  }

  async eliminarTramite(workspaceId: number, tramiteId: number): Promise<void> {
    await this.request(`/workspaces/${workspaceId}/tramites/${tramiteId}`, { method: "DELETE" });
  }

  async actualizarTramite(tramiteId: number, data: any): Promise<any> {
    return this.request(`/workspaces/tramites/${tramiteId}`, { method: "PATCH", body: JSON.stringify(data) });
  }

  async moverTramite(tramiteId: number, clienteIdDestino: number): Promise<void> {
    await this.request(`/tramites/${tramiteId}/mover`, {
      method: 'PATCH',
      body: JSON.stringify({ cliente_id_destino: clienteIdDestino }),
    });
  }

  async aprobarTramite(tramiteId: number, contenido: string): Promise<any> {
    return this.request(`/tramites/${tramiteId}/aprobar`, { 
      method: "POST", 
      body: JSON.stringify({ contenido }) 
    });
  }

  async obtenerSaludo(tramiteId: number): Promise<{ saludo: string }> {
    return this.request(`/tramites/${tramiteId}/saludo`);
  }

  // --- HISTORIAL DE CHAT (Mejora B) ---
  async obtenerHistorialChat(clienteId: number, modo: string = "creador"): Promise<any[]> {
    try {
      return await this.request(`/clientes/${clienteId}/mensajes?modo=${modo}`);
    } catch {
      return [];
    }
  }

  async guardarMensajeChat(clienteId: number, role: string, contenido: string, modo: string = "creador"): Promise<any> {
    return this.request(`/clientes/${clienteId}/mensajes`, {
      method: "POST",
      body: JSON.stringify({ role, contenido, modo })
    });
  }

  async limpiarHistorialChat(clienteId: number, modo: string = "creador"): Promise<void> {
    return this.request(`/clientes/${clienteId}/mensajes?modo=${modo}`, { method: "DELETE" });
  }

  // --- SESIONES DE CHAT (Gestor Global) ---
  async obtenerChatSessions(workspaceId: number): Promise<any[]> {
    return this.request(`/chat/workspaces/${workspaceId}/chat-sessions`);
  }

  async crearChatSession(workspaceId: number, titulo: string): Promise<any> {
    return this.request(`/chat/workspaces/${workspaceId}/chat-sessions`, { 
      method: "POST", 
      body: JSON.stringify({ titulo, tipo: "global" }) 
    });
  }

  async eliminarChatSession(workspaceId: number, sessionId: number): Promise<any> {
    return this.request(`/chat/workspaces/${workspaceId}/chat-sessions/${sessionId}`, { method: "DELETE" });
  }

  async obtenerMensajesChatSession(sessionId: number): Promise<any[]> {
    return this.request(`/chat/chat-sessions/${sessionId}/mensajes`);
  }

  async guardarMensajeChatSession(sessionId: number, role: string, contenido: string): Promise<any> {
    return this.request(`/chat/chat-sessions/${sessionId}/mensajes`, {
      method: "POST",
      body: JSON.stringify({ role, contenido })
    });
  }

  async obtenerArchivosTramite(tramiteId: number): Promise<any[]> {
    return this.request(`/tramites/${tramiteId}/archivos`);
  }

  async obtenerParticipaciones(tramiteId: number): Promise<any> {
    return this.request(`/tramites/${tramiteId}/participaciones`);
  }

  async checkHealth(): Promise<any> {
    try {
      // Usamos fetch directamente porque puede no estar bajo /api/v1
      const response = await fetch(`${BASE_URL.replace('/api/v1', '')}/health`);
      return await response.json();
    } catch {
      return { status: "offline", ollama: { status: "offline" } };
    }
  }

  async obtenerContenidoDocumento(docId: number): Promise<{ contenido: string }> {
    return this.request(`/tramites/documentos/${docId}/contenido`);
  }

  async guardarDocumento(workspaceId: number, nombre: string, contenido: string, clienteId?: number, tramiteId?: number): Promise<any> {
    // Crea un documento de texto en la librería del workspace
    const blob = new Blob([contenido], { type: 'text/plain' });
    const file = new File([blob], nombre, { type: 'text/plain' });
    return this.subirDocumento(workspaceId, file, tramiteId);
  }

  // --- CLIENTES ---
  async obtenerClientes(workspaceId: number): Promise<any[]> {
    // Intentamos la ruta del workspace, fallback a global si falla
    try {
      return await this.request(`/workspaces/${workspaceId}/clientes`);
    } catch {
      return this.request("/clientes");
    }
  }

  async crearCliente(workspaceId: number, data: any): Promise<any> {
    return this.request(`/workspaces/${workspaceId}/clientes`, { method: "POST", body: JSON.stringify(data) });
  }

  async editarCliente(workspaceId: number, clienteId: number, data: any): Promise<any> {
    return this.request(`/workspaces/${workspaceId}/clientes/${clienteId}`, { method: "PATCH", body: JSON.stringify(data) });
  }

  // --- EQUIPO ---
  async obtenerEquipo(workspaceId: number): Promise<any[]> {
    return this.request(`/workspaces/${workspaceId}/equipo`);
  }

  // --- LIBRO DE REQUERIMIENTOS ---
  async obtenerLibroRequerimientos(workspaceId: number): Promise<any[]> {
    return this.request(`/workspaces/${workspaceId}/libro`);
  }

  async crearAsientoLibro(workspaceId: number, data: any): Promise<any> {
    return this.request(`/workspaces/${workspaceId}/libro`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  // --- RAG & DOCUMENTOS ---
  async obtenerFuentesRag(workspaceId?: number): Promise<any[]> {
    const wsId = workspaceId || this.workspaceId || 1;
    try {
      return await this.request(`/workspaces/${wsId}/documentos`);
    } catch {
      // Fallback a fuentes estáticas del RAG global
      return (this.request("/generate/rag/sources") as Promise<any[]>).catch(() => [] as any[]);
    }
  }

  async subirDocumento(workspaceId: number, file: File, tramiteId?: number): Promise<any> {
    // Límite de 10MB estricto en cliente
    const MAX_MB = 10;
    if (file.size > MAX_MB * 1024 * 1024) {
      throw new Error(`El archivo excede el límite permitido de ${MAX_MB}MB.`);
    }

    const formData = new FormData();
    formData.append("file", file);
    if (tramiteId != null) {
      formData.append("tramite_id", String(tramiteId));
    }

    const response = await fetch(`${BASE_URL}/workspaces/${workspaceId}/documentos`, {
      method: "POST",
      headers: {
        ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
      },
      body: formData,
    });
    return response.json();
  }

  async generarCertificacion(data: any, params?: any): Promise<any> {
    const queryString = params ? `?nombre_escribano=${encodeURIComponent(params.nombre_escribano || '')}&nro_registro=${encodeURIComponent(params.nro_registro || '')}` : '';
    return this.request(`/generate/certificacion${queryString}`, { 
      method: "POST", 
      body: JSON.stringify(data) 
    });
  }

  async obtenerDocumentosGenerados(tramiteId: number): Promise<any[]> {
    try {
      return await this.request(`/tramites/${tramiteId}/documentos-generados`);
    } catch {
      return [];
    }
  }

  async ejecutarAuditoriaLegal(tramiteId: number): Promise<any> {
    return this.request(`/tramites/${tramiteId}/auditoria`, {
      method: "POST"
    });
  }

  async guardarDocumentoGenerado(tramiteId: number, nombre: string, contenido: string): Promise<any> {
    return this.request(`/tramites/${tramiteId}/documentos-generados`, {
      method: "POST",
      body: JSON.stringify({ nombre, contenido })
    });
  }

  async streamTramiteChat(
    mensaje: string,
    threadId: string,
    tenantId: string,
    history: { role: string; contenido: string }[] = [],
    modelo?: string,
    onEvent?: (event: any) => void,
    modo: string = "consultas",
    abortSignal?: AbortSignal,
    fuentesIds?: number[]
  ): Promise<void> {
    const url = `${BASE_URL}/documentos/chat/`;
    const payload: any = {
      mensaje,
      thread_id: threadId,
      tenant_id: tenantId,
      history: history.map(h => ({ role: h.role, contenido: h.contenido })),
      modo,
    };
    if (modelo) {
      payload.modelo = modelo;
    }
    if (fuentesIds && fuentesIds.length > 0) {
      payload.fuentes_ids = fuentesIds;
    }

    const response = await fetch(url, {
      method: 'POST',
      signal: abortSignal,
      headers: {
        'Content-Type': 'application/json',
        ...(this.token ? { Authorization: `Bearer ${this.token}` } : {})
      },
      body: JSON.stringify(payload),
    });
    
    if (!response.ok) throw new Error("Error en el stream del chat");
    if (!response.body) return;

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const dataStr = line.slice(6);
          if (dataStr === "[DONE]") {
            if (onEvent) onEvent({ event: "done" });
            return;
          }
          try {
            const parsed = JSON.parse(dataStr);
            if (onEvent) onEvent(parsed);
          } catch (e) {
            console.error("Error parsing SSE JSON:", e);
          }
        }
      }
    }
  }

  // --- EXPORTAR ---
  async descargarDocx(ruta: string, filename: string) {
    const response = await fetch(ruta, {
      headers: {
        ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
      }
    });
    if (!response.ok) throw new Error("Error al descargar archivo");
    
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  }

  async exportarDocumento(titulo: string, contenido: string, formato: "docx" | "pdf"): Promise<void> {
    // NOTE: BASE_URL already contains /api/v1, so we must NOT repeat it
    const response = await fetch(`${BASE_URL}/export`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(this.token ? { Authorization: `Bearer ${this.token}` } : {}),
      },
      body: JSON.stringify({ titulo, contenido, formato }),
    });

    if (!response.ok) throw new Error("Error al exportar documento");

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${titulo.replace(/ /g, '_')}.${formato}`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  }

  // --- Sistema ---
  async obtenerModelos(): Promise<string[]> {
    const res: any = await this.request('/sistema/modelos');
    return res.modelos || [];
  }

  async guardarContenidoDocumento(docId: number, contenido: string): Promise<any> {
    return this.request(`/tramites/documentos/${docId}/guardar`, {
      method: 'POST',
      body: JSON.stringify({ contenido }),
    });
  }

  async moverDocumento(docId: number, tramiteIdDestino: number): Promise<void> {
    await this.request(`/documentos/${docId}/mover`, {
      method: 'PATCH',
      body: JSON.stringify({ tramite_id_destino: tramiteIdDestino }),
    });
  }

  // --- Memoria Notarial ---
  async obtenerMemoriaNotarial(workspaceId: number): Promise<any[]> {
    return this.request(`/workspaces/${workspaceId}/memoria`, { method: "GET" });
  }

  async agregarReglaMemoria(workspaceId: number, regla: { preferencia: string, categoria: string }): Promise<any> {
    return this.request(`/workspaces/${workspaceId}/memoria`, {
      method: "POST",
      body: JSON.stringify(regla),
    });
  }

  async eliminarReglaMemoria(workspaceId: number, reglaId: number): Promise<void> {
    return this.request(`/workspaces/${workspaceId}/memoria/${reglaId}`, { method: "DELETE" });
  }

  // --- FINANZAS (Módulo ERP) ---
  async obtenerMovimientos(workspaceId: number, params?: { tipo?: string; fecha_desde?: string; fecha_hasta?: string; categoria_id?: number }): Promise<any[]> {
    const query = new URLSearchParams();
    if (params?.tipo) query.set("tipo", params.tipo);
    if (params?.fecha_desde) query.set("fecha_desde", params.fecha_desde);
    if (params?.fecha_hasta) query.set("fecha_hasta", params.fecha_hasta);
    if (params?.categoria_id) query.set("categoria_id", String(params.categoria_id));
    const qs = query.toString() ? `?${query.toString()}` : "";
    return this.request(`/workspaces/${workspaceId}/finanzas/movimientos${qs}`);
  }

  async crearMovimiento(workspaceId: number, data: any): Promise<any> {
    return this.request(`/workspaces/${workspaceId}/finanzas/movimientos`, { method: "POST", body: JSON.stringify(data) });
  }

  async actualizarMovimiento(workspaceId: number, movimientoId: number, data: any): Promise<any> {
    return this.request(`/workspaces/${workspaceId}/finanzas/movimientos/${movimientoId}`, { method: "PATCH", body: JSON.stringify(data) });
  }

  async eliminarMovimiento(workspaceId: number, movimientoId: number): Promise<void> {
    return this.request(`/workspaces/${workspaceId}/finanzas/movimientos/${movimientoId}`, { method: "DELETE" });
  }

  async obtenerResumenFinanciero(workspaceId: number, mes?: number, anio?: number): Promise<any> {
    const query = new URLSearchParams();
    if (mes) query.set("mes", String(mes));
    if (anio) query.set("anio", String(anio));
    const qs = query.toString() ? `?${query.toString()}` : "";
    return this.request(`/workspaces/${workspaceId}/finanzas/resumen${qs}`);
  }

  async obtenerFlujoCaja(workspaceId: number, meses: number = 12): Promise<any[]> {
    return this.request(`/workspaces/${workspaceId}/finanzas/flujo-caja?meses=${meses}`);
  }

  async obtenerCategoriasFinancieras(workspaceId: number): Promise<any[]> {
    return this.request(`/workspaces/${workspaceId}/finanzas/categorias`);
  }

  async crearCategoriaFinanciera(workspaceId: number, data: any): Promise<any> {
    return this.request(`/workspaces/${workspaceId}/finanzas/categorias`, { method: "POST", body: JSON.stringify(data) });
  }

  // --- PROVEEDORES ---
  async obtenerProveedores(workspaceId: number): Promise<any[]> {
    return this.request(`/workspaces/${workspaceId}/proveedores`);
  }

  async crearProveedor(workspaceId: number, data: any): Promise<any> {
    return this.request(`/workspaces/${workspaceId}/proveedores`, { method: "POST", body: JSON.stringify(data) });
  }

  async eliminarProveedor(workspaceId: number, proveedorId: number): Promise<void> {
    return this.request(`/workspaces/${workspaceId}/proveedores/${proveedorId}`, { method: "DELETE" });
  }

  // --- PRESUPUESTOS ---
  async obtenerPresupuestos(workspaceId: number, estado?: string): Promise<any[]> {
    const qs = estado ? `?estado=${estado}` : "";
    return this.request(`/workspaces/${workspaceId}/presupuestos${qs}`);
  }

  async crearPresupuesto(workspaceId: number, data: any): Promise<any> {
    return this.request(`/workspaces/${workspaceId}/presupuestos`, { method: "POST", body: JSON.stringify(data) });
  }

  async actualizarEstadoPresupuesto(workspaceId: number, presupuestoId: number, data: any): Promise<any> {
    return this.request(`/workspaces/${workspaceId}/presupuestos/${presupuestoId}`, { method: "PATCH", body: JSON.stringify(data) });
  }

  async eliminarPresupuesto(workspaceId: number, presupuestoId: number): Promise<void> {
    return this.request(`/workspaces/${workspaceId}/presupuestos/${presupuestoId}`, { method: "DELETE" });
  }

  async calcularAranceles(workspaceId: number, tipoActo: string, monto: number): Promise<any> {
    return this.request(`/workspaces/${workspaceId}/aranceles/calcular?tipo_acto=${encodeURIComponent(tipoActo)}&monto=${monto}`, { method: "POST" });
  }

  async obtenerAranceles(workspaceId: number): Promise<any[]> {
    return this.request(`/workspaces/${workspaceId}/aranceles`);
  }

  // --- AGENDA ---
  async obtenerEventos(workspaceId: number, params?: { fecha_desde?: string; fecha_hasta?: string; tipo?: string }): Promise<any[]> {
    const query = new URLSearchParams();
    if (params?.fecha_desde) query.set("fecha_desde", params.fecha_desde);
    if (params?.fecha_hasta) query.set("fecha_hasta", params.fecha_hasta);
    if (params?.tipo) query.set("tipo", params.tipo);
    const qs = query.toString() ? `?${query.toString()}` : "";
    return this.request(`/workspaces/${workspaceId}/agenda${qs}`);
  }

  async crearEvento(workspaceId: number, data: any): Promise<any> {
    return this.request(`/workspaces/${workspaceId}/agenda`, { method: "POST", body: JSON.stringify(data) });
  }

  async actualizarEvento(workspaceId: number, eventoId: number, data: any): Promise<any> {
    return this.request(`/workspaces/${workspaceId}/agenda/${eventoId}`, { method: "PATCH", body: JSON.stringify(data) });
  }

  async eliminarEvento(workspaceId: number, eventoId: number): Promise<void> {
    return this.request(`/workspaces/${workspaceId}/agenda/${eventoId}`, { method: "DELETE" });
  }

  async obtenerVencimientos(workspaceId: number, dias: number = 7): Promise<any[]> {
    return this.request(`/workspaces/${workspaceId}/agenda/vencimientos?dias=${dias}`);
  }

  // --- NOTAS ---
  async obtenerNotas(workspaceId: number, visibilidad?: string): Promise<any[]> {
    const qs = visibilidad ? `?visibilidad=${visibilidad}` : "";
    return this.request(`/workspaces/${workspaceId}/notas${qs}`);
  }

  async crearNota(workspaceId: number, data: any): Promise<any> {
    return this.request(`/workspaces/${workspaceId}/notas`, { method: "POST", body: JSON.stringify(data) });
  }

  async actualizarNota(workspaceId: number, notaId: number, data: any): Promise<any> {
    return this.request(`/workspaces/${workspaceId}/notas/${notaId}`, { method: "PATCH", body: JSON.stringify(data) });
  }

  async eliminarNota(workspaceId: number, notaId: number): Promise<void> {
    return this.request(`/workspaces/${workspaceId}/notas/${notaId}`, { method: "DELETE" });
  }

  // --- PLANTILLAS / BIBLIOTECA ---
  async obtenerPlantillas(workspaceId: number, categoria?: string): Promise<any[]> {
    const qs = categoria ? `?categoria=${categoria}` : "";
    return this.request(`/workspaces/${workspaceId}/plantillas${qs}`);
  }

  async crearPlantilla(workspaceId: number, data: any): Promise<any> {
    return this.request(`/workspaces/${workspaceId}/plantillas`, { method: "POST", body: JSON.stringify(data) });
  }

  async actualizarPlantilla(workspaceId: number, plantillaId: number, data: any): Promise<any> {
    return this.request(`/workspaces/${workspaceId}/plantillas/${plantillaId}`, { method: "PATCH", body: JSON.stringify(data) });
  }

  async usarPlantilla(workspaceId: number, plantillaId: number): Promise<any> {
    return this.request(`/workspaces/${workspaceId}/plantillas/${plantillaId}/usar`, { method: "POST" });
  }

  async eliminarPlantilla(workspaceId: number, plantillaId: number): Promise<void> {
    return this.request(`/workspaces/${workspaceId}/plantillas/${plantillaId}`, { method: "DELETE" });
  }

  // --- UIF / LAVADO ---
  async obtenerSujetosUIF(workspaceId: number): Promise<any[]> {
    return this.request(`/workspaces/${workspaceId}/uif/sujetos`);
  }

  // --- BUSCADOR GLOBAL ---
  async buscarGlobal(workspaceId: number, query: string): Promise<{clientes: any[], tramites: any[]}> {
    return this.request(`/search?workspace_id=${workspaceId}&q=${encodeURIComponent(query)}`);
  }
}

export const ofisolveApi = new OfiSolveApi();
