"""
Punto de entrada de la aplicación FastAPI.

Configura CORS, logging, y registra los routers de la API.
Ejecutar con: uvicorn main:app --reload --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from loguru import logger

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.database import Base, engine
from app.models.db_models import (
    Usuario, Workspace, Cliente, Tramite, Participacion, MensajeChat,
    CategoriaFinanciera, MovimientoFinanciero, Proveedor, Presupuesto,
    PresupuestoItem, EventoAgenda, Nota, ConfiguracionAranceles, PlantillaModelo,
)
from app.api.auth import router as auth_router
from app.api.routes_certificacion import router as certificacion_router
from app.api.routes_clientes import router as clientes_router
from app.api.routes_workspaces import router as workspaces_router
from app.api.routes_tramites import router as tramites_router
from app.api.routes_export import router as export_router
from app.api.routes_sistema import router as sistema_router
from app.api.routes_documentos import router as documentos_router
from app.api.routes_finanzas import router as finanzas_router
from app.api.routes_presupuestos import router as presupuestos_router
from app.api.routes_agenda import router as agenda_router
from app.api.routes_notas import router as notas_router
from app.api.routes_uif import router as uif_router
from app.api.onboarding import router as onboarding_router
from app.api.routes_chat import router as chat_router
from app.api.routes_search import router as search_router
from app.api.routes_protocolo import router as protocolo_router

# NOTA: routes_upload.py eliminado del main — su lógica fue integrada en routes_workspaces.py
# NOTA: routes_portal.py eliminado — era duplicado exacto de routes_tramites.py


async def _seed_initial_data(db_session) -> None:
    """
    Crea datos iniciales si la base de datos está completamente vacía.
    Esto garantiza que el frontend siempre tenga algo para mostrar en el primer arranque.
    """
    from sqlalchemy import select, func
    from app.core.security import get_password_hash
    import datetime as dt
    from decimal import Decimal

    # ¿Ya hay usuarios?
    result = await db_session.execute(select(func.count(Usuario.id)))
    if result.scalar() > 0:
        return  # Ya hay datos, no hacer nada

    logger.info("📦 Primera ejecución detectada — creando datos iniciales de demo...")

    # 1. Crear Workspace de demo
    ws = Workspace(
        nombre="Escribanía Demo",
        descripcion="Workspace de demostración. Podés renombrarlo en Configuración."
    )
    db_session.add(ws)
    await db_session.flush()

    # 2. Crear usuario administrador por defecto
    admin = Usuario(
        email="admin@ofisolve.com",
        hashed_password=get_password_hash("admin123"),
        nombre_completo="Escribano/a Demo",
        nro_matricula="001",
        escribania_nombre="Escribanía Demo",
        workspace_id=ws.id,
        rol="Escribano",
        is_active=True,
        is_superuser=True,
    )
    db_session.add(admin)
    await db_session.flush()

    # 3. Clientes de ejemplo
    # 3. Clientes de ejemplo realistas
    cliente1 = Cliente(
        workspace_id=ws.id,
        nombre_completo="Carlos Alberto Giménez",
        dni="24567890",
        cuit="20-24567890-5",
        email="carlos.gimenez75@gmail.com",
        telefono="11-4567-8901",
        domicilio="Av. Cabildo 2345, Piso 4, Depto B, CABA",
        tipo_persona="Fisica",
    )
    cliente2 = Cliente(
        workspace_id=ws.id,
        nombre_completo="Sofía Martínez",
        dni="32198765",
        cuit="27-32198765-8",
        email="smartinez@estudio-martinez.com.ar",
        telefono="11-6789-0123",
        domicilio="Talcahuano 450, Piso 2, CABA",
        tipo_persona="Fisica",
        riesgo_uif="Bajo",
        uif_estado="Aprobado",
        uif_ultima_revision=dt.datetime.now() - dt.timedelta(days=15)
    )
    cliente3 = Cliente(
        workspace_id=ws.id,
        nombre_completo="Desarrollos Inmobiliarios del Sur S.R.L.",
        dni="30712345678",
        cuit="30-71234567-8",
        email="legales@delsursrl.com.ar",
        telefono="11-4321-8765",
        domicilio="Av. del Libertador 5500, Oficina 301, CABA",
        tipo_persona="Juridica",
        riesgo_uif="Medio",
        uif_estado="En Análisis",
        uif_ultima_revision=dt.datetime.now() - dt.timedelta(days=5)
    )
    db_session.add_all([cliente1, cliente2, cliente3])
    await db_session.flush()

    # 4. Trámites de ejemplo realistas
    tramite1 = Tramite(
        workspace_id=ws.id,
        cliente_id=cliente1.id,
        nombre="Escritura de Compraventa Inmueble (Cabildo)",
        tipo="Escritura",
        estado="abierto",
        descripcion="Compraventa de la unidad funcional sita en Av. Cabildo 2345, CABA. Requiere COTI y libre deudas.",
    )
    tramite2 = Tramite(
        workspace_id=ws.id,
        cliente_id=cliente2.id,
        nombre="Constitución de Sociedad (Del Sur S.R.L.)",
        tipo="Constitución de Sociedad",
        estado="abierto",
        descripcion="Constitución por instrumento público de S.R.L. y designación de gerente.",
    )
    tramite3 = Tramite(
        workspace_id=ws.id,
        cliente_id=cliente3.id,
        nombre="Poder Especial Irrevocable (Desarrollos)",
        tipo="Poder",
        estado="completado",
        descripcion="Poder especial irrevocable post-mortem para escrituración de unidades funcionales.",
    )
    db_session.add_all([tramite1, tramite2, tramite3])
    await db_session.flush()

    # 5. Participaciones
    db_session.add_all([
        Participacion(cliente_id=cliente1.id, tramite_id=tramite1.id, rol="Vendedor"),
        Participacion(cliente_id=cliente2.id, tramite_id=tramite2.id, rol="Socia Gerente"),
        Participacion(cliente_id=cliente3.id, tramite_id=tramite3.id, rol="Poderdante"),
    ])

    await db_session.commit()
    logger.success("✅ Datos iniciales de demo creados correctamente.")
    logger.info("   👤 Usuario: admin@ofisolve.com / Contraseña: admin123")

    # ==========================================================================
    # SEED: Módulos ERP Competitivos
    # ==========================================================================

    logger.info("📦 Creando datos de demo para módulos ERP...")

    # --- Categorías Financieras (sistema, no eliminables) ---
    categorias = [
        CategoriaFinanciera(workspace_id=ws.id, nombre="Honorarios", tipo_default="ingreso", color="#10B981", icono="DollarSign", es_sistema=True),
        CategoriaFinanciera(workspace_id=ws.id, nombre="Sellos y Timbrados", tipo_default="egreso", color="#F59E0B", icono="Stamp", es_sistema=True),
        CategoriaFinanciera(workspace_id=ws.id, nombre="Aportes Caja Notarial", tipo_default="egreso", color="#8B5CF6", icono="Building2", es_sistema=True),
        CategoriaFinanciera(workspace_id=ws.id, nombre="Gastos Operativos", tipo_default="egreso", color="#EF4444", icono="Receipt", es_sistema=True),
        CategoriaFinanciera(workspace_id=ws.id, nombre="Gestorías y Trámites", tipo_default="egreso", color="#3B82F6", icono="FileSearch", es_sistema=True),
        CategoriaFinanciera(workspace_id=ws.id, nombre="Otros Ingresos", tipo_default="ingreso", color="#06B6D4", icono="Plus", es_sistema=False),
    ]
    db_session.add_all(categorias)
    await db_session.flush()

    # --- Aranceles Realistas (Colegio de Escribanos CABA - referencia) ---
    aranceles = [
        ConfiguracionAranceles(workspace_id=ws.id, concepto="Honorarios del Escribano", tipo_calculo="porcentaje", valor=Decimal("0.0200"), minimo=Decimal("150000"), aplica_a="todos", orden=1),
        ConfiguracionAranceles(workspace_id=ws.id, concepto="Impuesto de Sellos (CABA)", tipo_calculo="porcentaje", valor=Decimal("0.0360"), aplica_a="compraventa", orden=2),
        ConfiguracionAranceles(workspace_id=ws.id, concepto="Impuesto de Sellos (CABA)", tipo_calculo="porcentaje", valor=Decimal("0.0240"), aplica_a="hipoteca", orden=2),
        ConfiguracionAranceles(workspace_id=ws.id, concepto="Aporte Notarial (Ley 12990)", tipo_calculo="porcentaje", valor=Decimal("0.0050"), aplica_a="todos", orden=3),
        ConfiguracionAranceles(workspace_id=ws.id, concepto="Tasa de Justicia", tipo_calculo="porcentaje", valor=Decimal("0.0030"), aplica_a="todos", orden=4),
        ConfiguracionAranceles(workspace_id=ws.id, concepto="Certificado de Dominio (RPBA)", tipo_calculo="fijo", valor=Decimal("25000"), aplica_a="compraventa", orden=5),
        ConfiguracionAranceles(workspace_id=ws.id, concepto="Certificado de Inhibición", tipo_calculo="fijo", valor=Decimal("18000"), aplica_a="compraventa", orden=6),
        ConfiguracionAranceles(workspace_id=ws.id, concepto="Fojas de Actuación Notarial", tipo_calculo="fijo", valor=Decimal("8500"), aplica_a="todos", orden=7),
    ]
    db_session.add_all(aranceles)

    # --- Proveedores Demo ---
    prov1 = Proveedor(workspace_id=ws.id, nombre_completo="Gestoría Martínez & Asoc.", cuit="20-30456789-1", tipo="Gestor", telefono="11-4567-8901", email="gestoria@martinez.com.ar")
    prov2 = Proveedor(workspace_id=ws.id, nombre_completo="Registro de la Propiedad Inmueble", tipo="Registro", telefono="11-4000-0001")
    prov3 = Proveedor(workspace_id=ws.id, nombre_completo="Perito Ing. Carlos Ruiz", cuit="20-25678901-5", tipo="Perito", email="cruiz@peritos.com.ar")
    db_session.add_all([prov1, prov2, prov3])
    await db_session.flush()

    # --- Movimientos Financieros Demo ---
    hoy = dt.date.today()
    movimientos = [
        MovimientoFinanciero(workspace_id=ws.id, tipo="ingreso", monto=Decimal("850000"), descripcion="Honorarios Escritura Compraventa — Giménez", fecha=hoy - dt.timedelta(days=5), categoria_id=categorias[0].id, cliente_id=cliente1.id, estado="confirmado"),
        MovimientoFinanciero(workspace_id=ws.id, tipo="egreso", monto=Decimal("25000"), descripcion="Certificado de Dominio RPBA", fecha=hoy - dt.timedelta(days=4), categoria_id=categorias[4].id, proveedor_id=prov2.id, estado="confirmado"),
        MovimientoFinanciero(workspace_id=ws.id, tipo="egreso", monto=Decimal("180000"), descripcion="Sellos Provincia de Buenos Aires", fecha=hoy - dt.timedelta(days=3), categoria_id=categorias[1].id, estado="confirmado"),
        MovimientoFinanciero(workspace_id=ws.id, tipo="ingreso", monto=Decimal("120000"), descripcion="Honorarios Certificación Constitución — S.R.L.", fecha=hoy - dt.timedelta(days=1), categoria_id=categorias[0].id, cliente_id=cliente3.id, estado="pendiente"),
        MovimientoFinanciero(workspace_id=ws.id, tipo="egreso", monto=Decimal("45000"), descripcion="Aportes Caja Notarial — Mes corriente", fecha=hoy, categoria_id=categorias[2].id, estado="confirmado"),
    ]
    db_session.add_all(movimientos)

    # --- Presupuesto Demo ---
    presupuesto = Presupuesto(
        workspace_id=ws.id, cliente_id=cliente1.id, titulo="Presupuesto Compraventa Inmueble — Giménez",
        tipo_acto="Compraventa", monto_operacion=Decimal("60000000"), estado="enviado",
        fecha_envio=dt.datetime.utcnow(), observaciones="Inmueble en Av. Cabildo 2345, CABA.",
    )
    db_session.add(presupuesto)
    await db_session.flush()
    items_presupuesto = [
        PresupuestoItem(presupuesto_id=presupuesto.id, concepto="Honorarios del Escribano", monto=Decimal("1200000"), es_porcentaje=True, porcentaje_valor=Decimal("0.0200"), orden=1),
        PresupuestoItem(presupuesto_id=presupuesto.id, concepto="Impuesto de Sellos (CABA)", monto=Decimal("2160000"), es_porcentaje=True, porcentaje_valor=Decimal("0.0360"), orden=2),
        PresupuestoItem(presupuesto_id=presupuesto.id, concepto="Aporte Notarial", monto=Decimal("300000"), es_porcentaje=True, porcentaje_valor=Decimal("0.0050"), orden=3),
        PresupuestoItem(presupuesto_id=presupuesto.id, concepto="Certificado de Dominio e Inhibición", monto=Decimal("43000"), orden=4),
    ]
    db_session.add_all(items_presupuesto)

    # --- Eventos de Agenda Demo ---
    ahora = dt.datetime.utcnow()
    eventos = [
        EventoAgenda(workspace_id=ws.id, titulo="Firma Escritura — Giménez", tipo="turno", fecha_inicio=ahora + dt.timedelta(days=3, hours=10), fecha_fin=ahora + dt.timedelta(days=3, hours=11), cliente_id=cliente1.id, color="#3B82F6"),
        EventoAgenda(workspace_id=ws.id, titulo="Vencimiento Certificado Inhibición — S.R.L.", tipo="vencimiento", fecha_inicio=ahora + dt.timedelta(days=5), todo_el_dia=True, cliente_id=cliente3.id, color="#F59E0B"),
        EventoAgenda(workspace_id=ws.id, titulo="Firma Constitución de Sociedad — Martínez", tipo="turno", fecha_inicio=ahora + dt.timedelta(days=7, hours=14), fecha_fin=ahora + dt.timedelta(days=7, hours=16), cliente_id=cliente2.id, color="#8B5CF6"),
        EventoAgenda(workspace_id=ws.id, titulo="Recordatorio: Pago Matrícula Anual", tipo="recordatorio", fecha_inicio=ahora + dt.timedelta(days=14), todo_el_dia=True, color="#EF4444"),
    ]
    db_session.add_all(eventos)

    # --- Notas Demo ---
    notas = [
        Nota(workspace_id=ws.id, titulo="Pendiente: Pedir informe catastral", contenido="Para la escritura de Giménez, solicitar informe catastral (F2) actualizado a AGIP.", color="#FEF3C7", visibilidad="equipo", fijada=True),
        Nota(workspace_id=ws.id, titulo="Datos Registro Propiedad Inmueble CABA", contenido="Turnos online: rpi.gov.ar\nMesa de Entradas: Venezuela 1135.", color="#DBEAFE", visibilidad="equipo"),
        Nota(workspace_id=ws.id, titulo="Alícuotas Sellos Actualizadas", contenido="El nuevo cuadro tarifario fija el Impuesto de Sellos en 3,6% para transferencias de inmuebles en CABA.", color="#FDE2E2", visibilidad="personal"),
    ]
    db_session.add_all(notas)

    # --- Plantillas/Modelos Demo ---
    plantillas = [
        PlantillaModelo(
            workspace_id=ws.id,
            nombre="Modelo Escritura de Compraventa Inmueble (CABA)", 
            categoria="escritura", 
            descripcion="Modelo de escritura traslativa de dominio completa, con cláusulas UIF, ITI/Ganancias, y asentimiento conyugal.", 
            campos_requeridos='{"precio_monto": "string", "precio_moneda": "string", "direccion_inmueble": "string", "nomenclatura_catastral": "string", "certificado_dominio": "string", "coti_afip": "string", "asentimiento_conyugal": "boolean"}',
            contenido="ESCRITURA NÚMERO [NRO] — COMPRAVENTA — En la Ciudad Autónoma de Buenos Aires, a los [FECHA], ante mí, Escribano Público [NOMBRE_ESCRIBANO], titular del Registro Notarial N° [REG]...\n\nCOMPARECEN:\n- Por una parte, como VENDEDOR: [NOMBRE_VENDEDOR], argentino, mayor de edad, estado civil [ESTADO_CIVIL], DNI [DNI_VENDEDOR], CUIT/CUIL [CUIT_VENDEDOR], domiciliado en [DOMICILIO_VENDEDOR].\n- Por la otra, como COMPRADOR: [NOMBRE_COMPRADOR], argentino, mayor de edad, DNI [DNI_COMPRADOR], CUIT/CUIL [CUIT_COMPRADOR], domiciliado en [DOMICILIO_COMPRADOR].\n\nINTERVIENEN por sí mismos y DICEN: \nPRIMERO: Que el VENDEDOR VENDE Y TRANSFIERE al COMPRADOR, y éste compra, el inmueble ubicado en esta Ciudad Autónoma de Buenos Aires, sito en la calle [DIRECCIÓN_INMUEBLE], Unidad Funcional N° [UF], inscripto en el Registro de la Propiedad Inmueble bajo la Matrícula [MATRICULA]. Nomenclatura Catastral: Circunscripción [CIRC], Sección [SEC], Manzana [MANZ], Parcela [PARC].\n\nSEGUNDO: PRECIO. La venta se realiza por la suma total y convenida de DÓLARES ESTADOUNIDENSES BILLETE [MONTO_LETRAS] (U$S [MONTO_NUMEROS]), suma que el VENDEDOR declara haber recibido con anterioridad a este acto en dinero en efectivo, otorgando por la presente el más eficaz recibo y carta de pago.\n\nTERCERO: ASENTIMIENTO CONYUGAL. Presente en este acto el/la cónyuge del vendedor, [NOMBRE_CONYUGE], DNI [DNI_CONYUGE], manifiesta que presta su conformidad (Art. 456 del Código Civil y Comercial de la Nación).\n\nCUARTO: UIF y LEY 25.246. El COMPRADOR declara bajo juramento que los fondos aplicados a esta compraventa tienen origen lícito, provenientes de sus ingresos, y que [NO] reviste la condición de Persona Expuesta Políticamente (PEP).\n\nQUINTO: IMPUESTOS. Se han retenido y abonado los impuestos de sellos correspondientes, se obtuvo el COTI N° [COTI] y se procede a la retención de [ITI/GANANCIAS].\n\nLEÍDA QUE LES FUE, ratifican su contenido y firman por ante mí, DOY FE."
        ),
        PlantillaModelo(
            workspace_id=ws.id,
            nombre="Acta de Certificación de Firma (Libro)", 
            categoria="certificacion", 
            descripcion="Texto de requerimiento y certificación para libro de registro de firmas.", 
            campos_requeridos='{"titulo_documento": "string", "cantidad_fojas": "integer", "fecha_documento": "string"}',
            contenido="ACTA NÚMERO [NRO_CORRELATIVO] — CERTIFICACIÓN DE FIRMA — En la Ciudad Autónoma de Buenos Aires, a los [FECHA], ante mí, Escribano Público [NOMBRE_ESCRIBANO], titular del Registro Notarial N° [REG]...\n\nCOMPARECE: [REQUIRENTE], nacionalidad [NACIONALIDAD], mayor de edad, estado civil [ESTADO_CIVIL], titular del DNI [DNI], CUIT/CUIL [CUIT], con domicilio en [DOMICILIO], persona capaz, a quien de su identidad DOY FE por exhibición de su documento.\n\nY DICE: Que ME REQUIERE certificar la autenticidad de la firma que estampará en mi presencia en el documento adjunto, titulado \"[TITULO_DOCUMENTO_BASE]\", que consta de [CANTIDAD] fojas, fechado el [FECHA_DOCUMENTO].\n\nEfectuada la rogación, el requirente firma el documento de referencia y la presente acta, previa lectura y ratificación, por ante mí, DOY FE."
        ),
        PlantillaModelo(
            workspace_id=ws.id,
            nombre="Poder Especial Amplio Judicial y Administrativo", 
            categoria="poder", 
            descripcion="Poder especial amplio con facultades expresas para juicios y trámites administrativos.", 
            campos_requeridos='{"facultades_disposicion_incluidas": "boolean", "plazo_validez": "string", "fuero_especifico": "string"}',
            contenido="ESCRITURA NÚMERO [NRO] — PODER ESPECIAL — En la Ciudad Autónoma de Buenos Aires, a los [FECHA], ante mí...\n\nCOMPARECE: [PODERDANTE], DNI [DNI_PODERDANTE], CUIT [CUIT_PODERDANTE], con domicilio en [DOMICILIO_PODERDANTE], persona capaz a quien de su identidad DOY FE.\n\nY DICE: Que confiere PODER ESPECIAL, pero amplio y suficiente, a favor de [APODERADO], DNI [DNI_APODERADO], para que en su nombre y representación, actuando de forma conjunta o indistinta, lo represente en toda clase de juicios y trámites administrativos, ya sean civiles, comerciales, laborales, penales, o contencioso-administrativos, ante fueros Nacionales, Provinciales o Municipales.\n\nFACULTADES EXPRESSAS (Art. 375 CCCN): Se los faculta especialmente para iniciar y contestar demandas, oponer excepciones, prorrogar jurisdicción, recusar, transar, comprometer en árbitros, percibir sumas de dinero, otorgar recibos, absolver y poner posiciones, apelar, y realizar toda otra diligencia procesal requerida.\n\nDOY FE."
        ),
        PlantillaModelo(
            workspace_id=ws.id,
            nombre="Autorización de Viaje al Exterior (Menores)", 
            categoria="poder", 
            descripcion="Acorde a requerimientos de la Dirección Nacional de Migraciones.", 
            campos_requeridos='{"datos_menor_partida": "string", "paises_destino": "string", "datos_acompanante": "string", "viaja_solo": "boolean"}',
            contenido="ESCRITURA NÚMERO [NRO] — AUTORIZACIÓN DE VIAJE — En la Ciudad Autónoma de Buenos Aires, a los [FECHA]...\n\nCOMPARECEN: [MADRE/PADRE_1], DNI [DNI_1] y [MADRE/PADRE_2], DNI [DNI_2], ambos en ejercicio de la responsabilidad parental.\n\nY DICEN: Que AUTORIZAN expresamente a su hijo/a menor de edad [NOMBRE_MENOR], de nacionalidad argentina, nacido/a el [FECHA_NACIMIENTO], titular del DNI [DNI_MENOR] y pasaporte N° [PASAPORTE], para que pueda viajar dentro y fuera del país.\n\nDESTINOS: La presente autorización es amplia y válida para viajar a [PAISES_DESTINO], en compañía de [ACOMPAÑANTES] o sin compañía de adultos (viaje solo).\n\nACREDITACIÓN DE VÍNCULO: Se acredita la filiación mediante la exhibición de la Partida de Nacimiento expedida por [REGISTRO], inscripta bajo el Acta [ACTA], Tomo [TOMO], la cual tengo a la vista y en fotocopia agrego al protocolo.\n\nPLAZO: Esta autorización mantendrá su validez hasta la mayoría de edad del menor o hasta su revocación expresa.\n\nLEÍDA y ratificada, firman por ante mí, DOY FE."
        )
    ]

    db_session.add_all(plantillas)

    await db_session.commit()
    logger.success("✅ Datos ERP de demo creados: categorías, aranceles, proveedores, movimientos, presupuestos, agenda, notas y plantillas.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida de la aplicación."""
    from app.core.database import AsyncSessionLocal
    import asyncio

    setup_logging()
    settings = get_settings()

    max_retries = 5
    retry_delay = 2
    for i in range(max_retries):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.success("✅ Conexión a Base de Datos Local ESTABLECIDA.")
            break
        except Exception as e:
            if i < max_retries - 1:
                logger.warning(f"⚠️ Reintentando conexión ({i+1}/{max_retries}) en {retry_delay}s...")
                await asyncio.sleep(retry_delay)
            else:
                logger.error(f"❌ FALLO crítico de conexión: {str(e)}")

    # Seed de datos iniciales (solo si la DB está vacía)
    async with AsyncSessionLocal() as db:
        await _seed_initial_data(db)

    logger.info(
        "OfiSolve Backend iniciado",
        env=settings.app_env,
        sovereign_mode=True,
    )

    yield

    logger.info("OfiSolve Backend cerrando")


# ============================================================
# Instancia de la aplicación
# ============================================================

app = FastAPI(
    title="OfiSolve API",
    description=(
        "Sistema de IA para automatización de documentos notariales. "
        "Genera certificaciones, autorizaciones y poderes con anonimización "
        "de datos PII integrada. Human-in-the-Loop obligatorio."
    ),
    version="0.3.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ============================================================
# Rate Limiting & Security Middleware
# ============================================================

from app.api.dependencies import limiter

settings = get_settings()

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    if request.method == "OPTIONS":
        return await call_next(request)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# Routers — Un único punto de registro, sin duplicados
# ============================================================

app.include_router(auth_router,           prefix="/api/v1/auth",         tags=["Autenticación"])
app.include_router(certificacion_router,  prefix="/api/v1/generate",     tags=["Generación de Documentos"])
app.include_router(clientes_router,       prefix="/api/v1/clientes",     tags=["Clientes"])
app.include_router(workspaces_router,     prefix="/api/v1/workspaces",   tags=["Workspaces"])
app.include_router(tramites_router,       prefix="/api/v1/tramites",     tags=["Trámites & Chat"])
app.include_router(export_router,         prefix="/api/v1/export",       tags=["Exportación"])
app.include_router(sistema_router,        prefix="/api/v1/sistema",      tags=["Sistema"])
app.include_router(documentos_router,     prefix="/api/v1/documentos",   tags=["Documentos"])
app.include_router(onboarding_router,     prefix="/api/v1/onboarding",   tags=["Onboarding WEB"])
app.include_router(chat_router,           prefix="/api/v1/chat",         tags=["Chat"])
app.include_router(search_router,         prefix="/api/v1/search",       tags=["Búsqueda Global"])
app.include_router(protocolo_router,      prefix="/api/v1/protocolo",    tags=["Protocolo Notarial"])

# --- Módulos ERP Competitivos ---
app.include_router(finanzas_router,       prefix="/api/v1/workspaces",   tags=["Finanzas y Proveedores"])
app.include_router(presupuestos_router,   prefix="/api/v1/workspaces",   tags=["Presupuestos y Aranceles"])
app.include_router(agenda_router,         prefix="/api/v1/workspaces",   tags=["Agenda"])
app.include_router(notas_router,          prefix="/api/v1/workspaces",   tags=["Notas y Plantillas"])
app.include_router(uif_router,            prefix="/api/v1/workspaces",   tags=["UIF"])


# ============================================================
# Endpoints raíz
# ============================================================

@app.get("/", tags=["Sistema"])
async def root():
    return {
        "sistema": "OfiSolve",
        "version": "0.3.0",
        "descripcion": "Sistema de IA Notarial — Soberanía de datos local",
        "docs": "/docs",
        "estado": "operativo",
    }


@app.get("/health", tags=["Sistema"])
async def health():
    """Health check global del sistema."""
    import httpx
    
    if settings.ai_provider == "mock":
        ollama_status = "mock"
    else:
        ollama_status = "unknown"
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                r = await client.get(f"{settings.ollama_base_url}/api/tags")
                ollama_status = "online" if r.status_code == 200 else "error"
        except Exception:
            ollama_status = "offline"

    return {
        "status": "healthy",
        "version": "0.3.0",
        "services": {
            "api": "ok",
            "privacy_engine": "active (presidio)",
            "llm": f"ollama ({settings.ollama_llm_model}) — {ollama_status}",
            "database": "sqlite (local)",
            "rag": "chromadb (local)",
        },
        "ollama": {
            "status": ollama_status,
            "model": settings.ollama_llm_model,
            "embedding_model": settings.ollama_embedding_model,
        }
    }


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
