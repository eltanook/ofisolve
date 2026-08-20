from langchain_core.tools import tool
from loguru import logger
from sqlalchemy import select, update
from app.core.database import AsyncSessionLocal
from app.models.db_models import Cliente, Tramite, Presupuesto, EscrituraProtocolo

@tool
async def buscar_clientes(query: str) -> str:
    """
    Busca clientes en la base de datos por nombre o DNI/CUIT.
    Utiliza esto cuando el usuario te pregunte por la lista de clientes o por un cliente en específico.
    El parámetro query puede ser el nombre, DNI, o vacío para traer los últimos 20 clientes.
    """
    logger.info(f"[Tool] Buscando clientes con query: {query}")
    async with AsyncSessionLocal() as db:
        stmt = select(Cliente)
        if query and query.strip():
            stmt = stmt.where(
                (Cliente.nombre_completo.ilike(f"%{query}%")) |
                (Cliente.dni.ilike(f"%{query}%")) |
                (Cliente.cuit.ilike(f"%{query}%"))
            )
        stmt = stmt.limit(20)
        res = await db.execute(stmt)
        clientes = res.scalars().all()
        
        if not clientes:
            return "No se encontraron clientes."
            
        resultados = []
        for c in clientes:
            resultados.append(f"ID: {c.id} | Nombre: {c.nombre_completo} | DNI: {c.dni} | CUIT: {c.cuit} | Tipo: {c.tipo_persona}")
            
        return "\n".join(resultados)

@tool
async def obtener_perfil_cliente(cliente_id: int) -> str:
    """
    Obtiene todos los datos detallados de un cliente específico por su ID.
    Usa esta herramienta cuando necesites ver todos los datos (domicilio, nacimiento, UIF, PEP, etc) de un cliente.
    """
    logger.info(f"[Tool] Obteniendo perfil completo del cliente ID: {cliente_id}")
    async with AsyncSessionLocal() as db:
        stmt = select(Cliente).where(Cliente.id == cliente_id)
        res = await db.execute(stmt)
        cliente = res.scalars().first()
        
        if not cliente:
            return f"Error: Cliente con ID {cliente_id} no encontrado."
            
        cli_dict = cliente.__dict__
        cli_info = [f"{k}: {v}" for k, v in cli_dict.items() if k not in ["_sa_instance_state", "workspace_id", "fecha_creacion"] and v is not None]
        
        return "PERFIL DEL CLIENTE:\n" + "\n".join(cli_info)

@tool
async def actualizar_cliente(cliente_id: int, campo: str, nuevo_valor: str) -> str:
    """
    Actualiza un campo específico de un cliente en la base de datos.
    Los campos válidos son: nombre_completo, dni, cuit, email, telefono, domicilio, tipo_persona, sexo, variante_nombre, nacionalidad, tipo_documento, ejemplar_documento, estado_familia, nombre_padre, nombre_madre, domicilio_calle, domicilio_numero, domicilio_piso, domicilio_depto, domicilio_barrio, domicilio_localidad, domicilio_provincia, domicilio_pais, condicion_iva, riesgo_uif, es_pep.
    Usa esta herramienta SOLO cuando el usuario te pida EXPLÍCITAMENTE editar, actualizar o corregir un dato del cliente.
    """
    logger.info(f"[Tool] Actualizando cliente ID: {cliente_id}, campo: {campo} -> ***(PII Redacted)***")
    # Validate campo
    campos_permitidos = ["nombre_completo", "dni", "cuit", "email", "telefono", "domicilio", "tipo_persona", 
                         "sexo", "variante_nombre", "nacionalidad", "tipo_documento", "ejemplar_documento", 
                         "estado_familia", "nombre_padre", "nombre_madre", "domicilio_calle", "domicilio_numero", 
                         "domicilio_piso", "domicilio_depto", "domicilio_barrio", "domicilio_localidad", 
                         "domicilio_provincia", "domicilio_pais", "condicion_iva", "riesgo_uif"]
    
    # Manejar booleanos
    valor_final = nuevo_valor
    if campo == "es_pep":
        valor_final = True if nuevo_valor.lower() in ['true', 'si', 'sí', '1'] else False
        campos_permitidos.append("es_pep")
        
    if campo not in campos_permitidos:
        return f"Error: El campo '{campo}' no es válido o no está permitido editarlo."
        
    try:
        async with AsyncSessionLocal() as db:
            stmt = update(Cliente).where(Cliente.id == cliente_id).values({campo: valor_final})
            await db.execute(stmt)
            await db.commit()
            return f"¡Éxito! El campo '{campo}' del cliente {cliente_id} fue actualizado a '{nuevo_valor}' en la base de datos."
    except Exception as e:
        logger.error(f"[Tool Error] Fallo al actualizar cliente: {e}")
        return f"Error crítico al actualizar base de datos: {str(e)}"

@tool
async def buscar_tramites(query: str, cliente_id: int = None) -> str:
    """
    Busca carpetas/trámites en la escribanía. 
    Usa esto si el usuario pregunta por los trámites abiertos, pendientes o asignados a un cliente.
    Puedes pasar un query (nombre del trámite) o un cliente_id para filtrar, o ambos vacíos para traer los últimos 20.
    """
    logger.info(f"[Tool] Buscando trámites con query: {query}, cliente_id: {cliente_id}")
    try:
        async with AsyncSessionLocal() as db:
            stmt = select(Tramite)
            if query and query.strip():
                stmt = stmt.where(Tramite.nombre.ilike(f"%{query}%"))
            if cliente_id:
                stmt = stmt.where(Tramite.cliente_id == cliente_id)
            stmt = stmt.limit(20)
            res = await db.execute(stmt)
            tramites = res.scalars().all()
            
            if not tramites:
                return "No se encontraron trámites con esos criterios."
                
            resultados = []
            for t in tramites:
                resultados.append(f"Trámite ID: {t.id} | Nombre: {t.nombre} | Tipo: {t.tipo} | Estado: {t.estado} | Cliente ID: {t.cliente_id}")
            return "\n".join(resultados)
    except Exception as e:
        logger.error(f"[Tool Error] Fallo al buscar tramites: {e}")
        return "Error al leer los trámites en la base de datos."

@tool
async def obtener_presupuestos(cliente_id: int) -> str:
    """
    Obtiene la situación financiera (presupuestos) de un cliente.
    Usa esto si el usuario te pregunta por las deudas, facturación o presupuestos de un cliente.
    """
    logger.info(f"[Tool] Obteniendo presupuestos del cliente: {cliente_id}")
    try:
        async with AsyncSessionLocal() as db:
            stmt = select(Presupuesto).where(Presupuesto.cliente_id == cliente_id)
            res = await db.execute(stmt)
            presupuestos = res.scalars().all()
            
            if not presupuestos:
                return f"El cliente {cliente_id} no tiene presupuestos registrados."
                
            resultados = []
            for p in presupuestos:
                estado = getattr(p, 'estado', 'desconocido')
                total = getattr(p, 'total', '0')
                resultados.append(f"Presupuesto ID: {p.id} | Trámite ID: {p.tramite_id} | Estado: {estado} | Total: ${total}")
            return "\n".join(resultados)
    except Exception as e:
        logger.error(f"[Tool Error] Fallo al obtener presupuestos: {e}")
        return "Error al consultar las finanzas en la base de datos."

@tool
async def buscar_escrituras(anio: int = None, tramite_id: int = None) -> str:
    """
    Busca Escrituras Públicas en el Protocolo Notarial.
    Usa esto si el usuario te pregunta sobre escrituras otorgadas, números de escritura, tomos, o folios.
    Puedes filtrar por año (anio) o por el ID del trámite (tramite_id).
    """
    logger.info(f"[Tool] Buscando escrituras anio: {anio}, tramite_id: {tramite_id}")
    try:
        async with AsyncSessionLocal() as db:
            stmt = select(EscrituraProtocolo)
            if anio:
                stmt = stmt.where(EscrituraProtocolo.anio == anio)
            if tramite_id:
                stmt = stmt.where(EscrituraProtocolo.tramite_id == tramite_id)
            
            stmt = stmt.order_by(EscrituraProtocolo.numero_escritura.desc()).limit(20)
            res = await db.execute(stmt)
            escrituras = res.scalars().all()
            
            if not escrituras:
                return "No se encontraron escrituras en el Protocolo con esos filtros."
                
            resultados = []
            for e in escrituras:
                resultados.append(f"Escritura N°: {e.numero_escritura}/{e.anio} | Tipo: {e.tipo_acto} | Tomo: {e.tomo} | Folios: {e.folio_inicio}-{e.folio_fin} | Trámite ID: {e.tramite_id}")
            return "\n".join(resultados)
    except Exception as e:
        logger.error(f"[Tool Error] Fallo al buscar escrituras: {e}")
        return "Error al leer el Protocolo Notarial en la base de datos."

client_tools = [buscar_clientes, obtener_perfil_cliente, actualizar_cliente, buscar_tramites, obtener_presupuestos, buscar_escrituras]
