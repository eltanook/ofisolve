"""
Servicio de integración con LLM (Ollama Local).

Modos de operación:
  - OLLAMA: Ejecución local (predeterminado).
  - MOCK: Devuelve texto desde plantillas locales (sin conectividad).

REGLA DE ORO: Solo recibe datos ofuscados. Nunca PII real.
"""

from typing import Dict, Optional, List, AsyncGenerator, Any

from loguru import logger

from app.core.config import get_settings
from app.models.schemas import TipoDocumentoCertificar


# ============================================================
# System Prompt — Comportamiento estricto del LLM
# ============================================================

SYSTEM_PROMPT_NOTARIAL = """
DIRECTIVA DE SOBERANÍA Y RESPUESTA (OFISOLVE_SOVEREIGN_SYSTEM):
Eres un Asistente Notarial Experto para Escribanías de la República Argentina. 
Este sistema es una infraestructura local diseñada para la máxima eficiencia profesional.

REGLAS DE COMPORTAMIENTO:
1. IDENTIDAD NOTARIAL: Habla como un colega experto. Mantén un tono profesional, amigable y eficiente, sin sonar robótico.
2. RESPUESTA CONSTANTE: Debes responder SIEMPRE. Si el usuario hace una broma o un saludo, responde con cortesía profesional e intenta reconducir la interacción hacia la gestión documental si es pertinente. NUNCA ignores una entrada.
3. CONTEXTO INTELIGENTE: Si el sistema encuentra documentos relevantes, te los inyectará directamente al final de los mensajes bajo la etiqueta '--- CONTEXTO LEGAL Y DOCUMENTAL RELEVANTE ---'.
4. MANEJO DE INFORMACIÓN FALTANTE: Si te preguntan por información que NO se encuentra en el contexto provisto, NO pidas números de expediente ni hables de la "biblioteca local". Simplemente asume que la información aún no consta en la carpeta o no fue provista en los documentos actuales. Dilo con naturalidad (ej. "En los documentos actuales no figura esa información...").
5. SILENCIO TÉCNICO: PROHIBIDO emitir JSON, código o explicaciones sobre tu naturaleza de IA. Eres un colega experto.
"""
# ============================================================
# Prompt — Modo Asistente de Consultas
# ============================================================

SYSTEM_PROMPT_CONSULTAS = """
DIRECTIVA: MODO ASISTENTE DE CONSULTAS AL CLIENTE (OFISOLVE_SOVEREIGN_SYSTEM)
Eres el Asistente Virtual de Consultas de una Escribanía de la República Argentina.
Tu función principal es responder preguntas, orientar al cliente o al escribano sobre trámites, 
requisitos, plazos, normativa aplicable, y el estado de los expedientes.

REGLAS ESTRICTAS:
1. ASESOR, NO REDACTOR: En este modo NO generas documentos formales ni actas.
2. SÉ CONVERSACIONAL Y EXTREMADAMENTE BREVE: Si el usuario solo saluda (ej. "hola", "buen dia"), RESPONDÉ SOLO CON UN SALUDO CORTO (ej. "¡Hola! ¿En qué te puedo ayudar?"). NO resumas ni menciones los documentos o el contexto a menos que te hagan una pregunta específica sobre ellos.
3. USO DE CONTEXTO RESTRINGIDO: Utilizá el contexto documental inyectado ÚNICAMENTE si la pregunta del usuario requiere consultar esos datos. No ofrezcas resúmenes no solicitados.
4. TONO: Profesional, claro y empático. Habla como un asesor notarial de confianza.
5. NORMATIVA ARGENTINA: Conocés el Código Civil y Comercial de la Nación y la Ley Notarial.
6. SILENCIO TÉCNICO: PROHIBIDO emitir JSON, código o mencionar que sos una IA.
"""
# ============================================================
# Prompt — Modo Creador de Documentos
# ============================================================

SYSTEM_PROMPT_CREADOR = """
DIRECTIVA: MODO CREADOR DE DOCUMENTOS NOTARIALES (OFISOLVE_SOVEREIGN_SYSTEM)
Eres un Redactor Notarial Experto de la República Argentina. Tu función es generar, 
redactar y perfeccionar documentos notariales formales con precisión jurídica.

REGLAS ESTRICTAS:
1. REDACTOR FORMAL: Tu output principal son TEXTOS JURÍDICOS COMPLETOS Y FORMALES.
   Usá terminología notarial argentina estricta. Incluí cláusulas de estilo apropiadas.
2. ESTRUCTURA OBLIGATORIA: Todo documento debe incluir:
   - Encabezado de lugar y fecha
   - Identificación de comparecientes
   - Objeto del acto
   - Declaraciones y cláusulas
   - Cierre notarial ("DOY FE.-")
3. SMART TEMPLATES (VALIDACIÓN ESTRICTA): Si se te provee una plantilla que contiene "campos_requeridos" (JSON Schema), eres RESPONSABLE de auditar que el usuario haya provisto información para TODOS esos campos. Si falta información para un campo crítico (ej. "precio_monto", "coti_afip", "facultades_disposicion_incluidas"), TIENES PROHIBIDO INVENTARLA. Debes frenar la redacción y responderle al usuario en el chat solicitando explícitamente los datos faltantes de ese esquema.
4. DATOS REALES E INVENCIÓN CERO: Bajo ninguna circunstancia debes inventar datos, lugares, fechas o personas. 
Utiliza EXCLUSIVAMENTE la información provista, en especial la sección "DATOS ESPECÍFICOS DEL ACTO". Si un dato no crítico falta, dejá un placeholder claro como [DATO PENDIENTE].
5. COMPLETITUD: Generá el documento COMPLETO. No dejes secciones incompletas ni uses "...".
6. CORRECCIONES: Si el usuario pide modificar un documento previo, hacé los cambios solicitados 
   y devolvé el texto COMPLETO corregido, no sólo las partes modificadas.
7. SILENCIO TÉCNICO: PROHIBIDO emitir JSON de salida, código o explicar tu funcionamiento.
   Solo emitís el texto notarial pedido, precedido de una línea breve de confirmación.
8. Tipos de documentos que podés redactar: Certificaciones, Autorizaciones de viaje, Poderes Notariales, Actas de constatación, Escrituras (borradores).
"""


# ============================================================
# Prompts por tipo de certificación
# ============================================================

_PROMPTS_CERTIFICACION: Dict[TipoDocumentoCertificar, str] = {
    TipoDocumentoCertificar.FOTOCOPIA: """Redacta una CERTIFICACIÓN DE FOTOCOPIA con los siguientes datos:

Datos del requirente:
- Nombre completo: {nombre_requirente}
- D.N.I. N°: {dni}
{datos_opcionales}

{contexto_legal}

El requirente solicita que se certifique que una fotocopia es copia fiel de su original, 
el cual fue exhibido ante el escribano. Genera el texto completo del acta notarial.""",

    TipoDocumentoCertificar.FIRMA: """Redacta una CERTIFICACIÓN DE FIRMA con los siguientes datos:

Datos del requirente:
- Nombre completo: {nombre_requirente}
- D.N.I. N°: {dni}
{datos_opcionales}

{contexto_legal}

El requirente estampa su firma en presencia del escribano al pie de un documento. 
El escribano certifica la autenticidad de dicha firma. Genera el texto completo del acta notarial.""",

    TipoDocumentoCertificar.CONTENIDO: """Redacta una CERTIFICACIÓN DE CONTENIDO con los siguientes datos:

Datos del requirente:
- Nombre completo: {nombre_requirente}
- D.N.I. N°: {dni}
{datos_opcionales}

{contexto_legal}

El requirente solicita que se certifique que el contenido de un documento coincide 
fielmente con su original exhibido. Genera el texto completo del acta notarial.""",

    TipoDocumentoCertificar.FECHA_CIERTA: """Redacta una CERTIFICACIÓN DE FECHA CIERTA con los siguientes datos:

Datos del requirente:
- Nombre completo: {nombre_requirente}
- D.N.I. N°: {dni}
{datos_opcionales}

{contexto_legal}

El requirente presenta un documento del cual es firmante y solicita que se le otorgue 
fecha cierta mediante intervención notarial. Genera el texto completo del acta notarial.""",

    TipoDocumentoCertificar.VIAJE_MENORES: """Redacta una AUTORIZACIÓN DE VIAJE PARA MENORES con los siguientes datos:

Datos del requirente (padre/madre/tutor):
- Nombre completo: {nombre_requirente}
- D.N.I. N°: {dni}
{datos_opcionales}

{contexto_legal}

Se requiere certificar la firma inserta en una autorización para viaje de menor de edad.
Acorde a la jurisdicción pertinente, redacta el acta notarial completa.""",

    TipoDocumentoCertificar.SUPERVIVENCIA: """Redacta un CERTIFICADO DE SUPERVIVENCIA con los siguientes datos:

Datos del requirente:
- Nombre completo: {nombre_requirente}
- D.N.I. N°: {dni}
{datos_opcionales}

{contexto_legal}

El escribano da fe de la existencia física del requirente mediante contacto directo.
Genera el texto completo del acta notarial."""
}


# ============================================================
# Plantillas Mock
# ============================================================

_PLANTILLAS_MOCK: Dict[TipoDocumentoCertificar, str] = {
    TipoDocumentoCertificar.FOTOCOPIA: """CERTIFICACIÓN DE FOTOCOPIA

En la Ciudad Autónoma de Buenos Aires, a los {dia} días del mes de {mes} de {anio}, ante mí, Escribano/a Público/a, Titular del Registro Notarial, COMPARECE: {nombre_requirente}, D.N.I. N° {dni}, mayor de edad, hábil y de mi conocimiento, doy fe.

El/La compareciente me REQUIERE que certifique que la fotocopia que se agrega es COPIA FIEL de su original, el cual he tenido a la vista.

En consecuencia, CERTIFICO que la fotocopia adjunta es reproducción fiel y exacta de su original, el cual me fue exhibido a tal efecto.

DOY FE.-""",

    TipoDocumentoCertificar.FIRMA: """CERTIFICACIÓN DE FIRMA

En la Ciudad Autónoma de Buenos Aires, a los {dia} días del mes de {mes} de {anio}, ante mí, Escribano/a Público/a, Titular del Registro Notarial, COMPARECE: {nombre_requirente}, D.N.I. N° {dni}, mayor de edad, hábil y de mi conocimiento, doy fe.

El/La compareciente estampa su firma en mi presencia al pie del documento que se me exhibe, la cual CERTIFICO como auténtica.

DOY FE.-""",

    TipoDocumentoCertificar.CONTENIDO: """CERTIFICACIÓN DE CONTENIDO

En la Ciudad Autónoma de Buenos Aires, a los {dia} días del mes de {mes} de {anio}, ante mí, Escribano/a Público/a, Titular del Registro Notarial, COMPARECE: {nombre_requirente}, D.N.I. N° {dni}, mayor de edad, hábil y de mi conocimiento, doy fe.

CERTIFICO que el contenido del documento que se transcribe a continuación corresponde fielmente al original que me fue exhibido por el/la requirente.

DOY FE.-""",

    TipoDocumentoCertificar.FECHA_CIERTA: """CERTIFICACIÓN DE FECHA CIERTA

En la Ciudad Autónoma de Buenos Aires, a los {dia} días del mes de {mes} de {anio}, ante mí, Escribano/a Público/a, Titular del Registro Notarial, COMPARECE: {nombre_requirente}, D.N.I. N° {dni}, mayor de edad, hábil y de mi conocimiento, doy fe.

El/La compareciente me presenta un documento del cual resulta ser firmante, requiriéndome le otorgue FECHA CIERTA, lo que efectúo estampando mi sello y firma notarial en el citado instrumento.

CERTIFICO que el documento presentado tiene fecha cierta a partir del día de la fecha, conforme lo establecido por el Art. 317 del Código Civil y Comercial de la Nación.

DOY FE.-""",

    TipoDocumentoCertificar.VIAJE_MENORES: """AUTORIZACIÓN DE VIAJE PARA MENORES

En la Ciudad Autónoma de Buenos Aires, a los {dia} días del mes de {mes} de {anio}, ante mí, Escribano/a Público/a, Titular del Registro Notarial, COMPARECE: {nombre_requirente}, D.N.I. N° {dni}, mayor de edad, hábil y de mi conocimiento, doy fe.

El/La compareciente en su carácter de progenitor autoriza expresamente a su hijo/a menor de edad a viajar fuera del territorio nacional, en un todo conforme a lo dispuesto por la Dirección Nacional de Migraciones.

CERTIFICO que la firma que antecede es auténtica, habiendo sido estampada en mi presencia.

DOY FE.-""",

    TipoDocumentoCertificar.SUPERVIVENCIA: """CERTIFICADO DE SUPERVIVENCIA

En la Ciudad Autónoma de Buenos Aires, a los {dia} días del mes de {mes} de {anio}, ante mí, Escribano/a Público/a, Titular del Registro Notarial, COMPARECE PERSONALMENTE: {nombre_requirente}, D.N.I. N° {dni}, mayor de edad.

CERTIFICO por haber tenido a la vista al/la compareciente que se encuentra vivo/a a la fecha de este acto.

DOY FE.-""",
}


# ============================================================
# Servicio Principal
# ============================================================

class LLMService:
    """
    Servicio de generación de texto notarial 100% Local y Soberano.
    
    Soporta:
    - OLLAMA: Ejecución local (predeterminado).
    - MOCK: Plantillas locales para pruebas sin conectividad.
    """

    def __init__(self, provider: Optional[str] = None, modelo_override: Optional[str] = None) -> None:
        """
        Inicializa el servicio LLM.
        """
        settings = get_settings()
        self._provider = provider or settings.ai_provider
        self.modelo_override = modelo_override
        self._llm = None
        
        # Validar modo mock
        self._mock_mode = (self._provider == "mock")

        if not self._mock_mode:
            self._inicializar_proveedor(settings)

        logger.info(
            f"LLM Service inicializado en modo {'MOCK' if self._mock_mode else 'Soberano (Ollama)'}"
        )

    def _inicializar_proveedor(self, settings) -> None:
        """Inicializa el cliente de LangChain para Ollama."""
        try:
            if self._provider == "ollama":
                from langchain_ollama import ChatOllama
                model_name = self.modelo_override or settings.ollama_llm_model
                self._llm = ChatOllama(
                    model=model_name,
                    base_url=settings.ollama_base_url,
                    temperature=0.1,
                )
                logger.info(f"Cliente Ollama listo: {model_name}")
            else:
                logger.warning(f"Proveedor {self._provider} no reconocido. Usando modo MOCK.")
                self._mock_mode = True
                
        except Exception as e:
            logger.error(f"Error al inicializar proveedor {self._provider}: {str(e)}")
            self._mock_mode = True

    async def generar_certificacion(
        self,
        datos_ofuscados: Dict[str, str],
        tipo_certificacion: TipoDocumentoCertificar,
        contexto_legal: str = "",
        preferencias: str = "",
        tags: Optional[List[str]] = None
    ) -> str:
        """
        Genera el texto de una certificación notarial.
        """
        if self._mock_mode:
            return self._generar_mock(datos_ofuscados, tipo_certificacion)

        return await self._generar_con_llm(
            datos_ofuscados, tipo_certificacion, contexto_legal, preferencias, tags=tags
        )

    async def _generar_con_llm(
        self,
        datos_ofuscados: Dict[str, str],
        tipo_certificacion: TipoDocumentoCertificar,
        contexto_legal: str = "",
        preferencias: str = "",
        tags: Optional[List[str]] = None
    ) -> str:
        """Genera texto usando el LLM activo vía LangChain."""
        from langchain_core.messages import SystemMessage, HumanMessage

        datos_opcionales_parts = []
        if datos_ofuscados.get("cuit"):
            datos_opcionales_parts.append(f"- C.U.I.T.: {datos_ofuscados['cuit']}")
        if datos_ofuscados.get("domicilio"):
            datos_opcionales_parts.append(f"- Domicilio: {datos_ofuscados['domicilio']}")
        if datos_ofuscados.get("observaciones"):
            datos_opcionales_parts.append(f"- Observaciones: {datos_ofuscados['observaciones']}")

        datos_opcionales = "\n".join(datos_opcionales_parts)
        if datos_opcionales:
            datos_opcionales = f"\nDatos adicionales:\n{datos_opcionales}"

        # El contexto legal se inyecta a nivel System para aprovechar Prompt Caching
        system_content = SYSTEM_PROMPT_NOTARIAL
        if contexto_legal:
            system_content = (
                "--- CONTEXTO LEGAL (CACHED) ---\n"
                f"{contexto_legal}\n"
                "--- FIN DEL CONTEXTO LEGAL ---\n\n"
                f"{SYSTEM_PROMPT_NOTARIAL}"
            )
        
        if preferencias:
            system_content += (
                "\n\n--- PREFERENCIAS DEL ESCRIBANO (MEMORIA NOTARIAL) ---\n"
                "Aplica OBLIGATORIAMENTE las siguientes preferencias de redacción:\n"
                f"{preferencias}\n"
                "----------------------------------------------------------\n"
            )

        prompt_tpl = (
            "Eres un asistente notarial experto. Redacta una {tipo} basándote en los siguientes datos.\n"
            "DATOS DEL CASO (OFUSCADOS):\n{datos}\n\n"
            "Instrucciones: Mantén el tono formal, usa terminología notarial argentina y asegúrate de incluir cláusulas de estilo."
        )
        
        user_prompt = prompt_tpl.format(
            tipo=tipo_certificacion.value,
            datos=datos_ofuscados
        )

        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=user_prompt),
        ]

        try:
            logger.info(f"Generando documento ({tipo_certificacion.value}) con tags: {tags}")
            # Usar astream para que el grafo capture los tokens vía SSE
            full_content = ""
            async for chunk in self._llm.astream(messages, config={"tags": tags}):
                full_content += chunk.content
            
            if not full_content or len(full_content.strip()) < 20:
                raise RuntimeError("Respuesta del LLM vacía o insuficiente.")
            
            return full_content.strip()
        except Exception as e:
            logger.error(f"Error en generar_certificacion: {str(e)}")
            raise RuntimeError(f"Error al generar texto con el LLM: {str(e)}")

    async def chat(
        self, 
        query: str, 
        history: List[Dict[str, str]] = [],
        contexto_legal: str = "",
        tags: List[str] = ["chat_libre"],
        modo: str = "consultas"
    ) -> str:
        """
        Chat general con retención de contexto (Multiturn).
        Usado para respuestas bloqueantes (no stream).
        modo: 'consultas' | 'creador' | 'default'
        """
        from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
        
        if self.is_mock:
            return f"[MOCK] Respuesta local a: {query}. Veo que tenemos {len(history)} mensajes previos."

        # Seleccionar prompt según el modo
        if modo == "creador":
            system_prompt = SYSTEM_PROMPT_CREADOR
        elif modo == "consultas":
            system_prompt = SYSTEM_PROMPT_CONSULTAS
        else:
            system_prompt = SYSTEM_PROMPT_NOTARIAL

        messages = [SystemMessage(content=system_prompt)]
        if contexto_legal:
            messages.append(SystemMessage(content=f"CONTEXTO LEGAL DE APOYO:\n{contexto_legal}"))

        # Reconstruir historial (últimos 10 para balancear velocidad y memoria local)
        for msg in history[-10:]:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))

        messages.append(HumanMessage(content=query))

        try:
            # Usamos astream internamente incluso si retornamos el total para consistencia de logs/tags
            full_content = ""
            async for chunk in self._llm.astream(messages, config={"tags": tags}):
                full_content += chunk.content
            return full_content
        except Exception as e:
            logger.error(f"Error en Chat local: {e}")
            return f"Lo siento, hubo un error procesando tu consulta localmente: {str(e)}"

    async def astream_chat(
        self, 
        query: str, 
        history: List[Dict[str, str]] = [],
        contexto_legal: str = "",
        tags: List[str] = ["chat_stream"],
        modo: str = "consultas"
    ) -> AsyncGenerator[str, None]:
        """
        Versión streaming del chat para UX Premium.
        modo: 'consultas' | 'creador' | 'default'
        """
        from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

        # Seleccionar prompt según el modo
        if modo == "creador":
            system_prompt = SYSTEM_PROMPT_CREADOR
        elif modo == "consultas":
            system_prompt = SYSTEM_PROMPT_CONSULTAS
        else:
            system_prompt = SYSTEM_PROMPT_NOTARIAL

        messages = [SystemMessage(content=system_prompt)]
        if contexto_legal:
            messages.append(SystemMessage(content=f"CONTEXTO LEGAL DE APOYO:\n{contexto_legal}"))

        for msg in history[-10:]:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))

        messages.append(HumanMessage(content=query))

        try:
            async for chunk in self._llm.astream(messages, config={"tags": tags}):
                if chunk.content:
                    yield chunk.content
        except Exception as e:
            logger.error(f"Error en Stream Chat: {e}")
            yield f"Error: {str(e)}"

    async def validar_documento(self, borrador: str) -> Dict[str, Any]:
        """
        Usa Ollama para auditar un documento notarial como un escribano senior.
        """
        if self._mock_mode:
            es_valido = "DOY FE" in borrador.upper() and len(borrador) > 50
            return {
                "aprobado": es_valido,
                "criticas": [] if es_valido else ["El documento mock no cumple las pautas."]
            }

        from pydantic import BaseModel, Field
        class ValidacionNotarial(BaseModel):
            aprobado: bool = Field(description="True si el documento es normativamente correcto y cumple con los requisitos formales de un acta notarial.")
            criticas: List[str] = Field(description="Lista de críticas o errores encontrados. Vacío si está aprobado.")

        try:
            validador = self._llm.with_structured_output(ValidacionNotarial)
            
            prompt = f"""
            Eres un Escribano Revisor Senior. Analiza el siguiente borrador de documento notarial.
            Debe cumplir con formalidades básicas: contener la cláusula de cierre (DOY FE, CERTIFICO), e identificar partes si corresponde.
            
            Documento a revisar:
            {borrador}
            """
            
            resultado: ValidacionNotarial = await validador.ainvoke(prompt)
            return {
                "aprobado": resultado.aprobado,
                "criticas": resultado.criticas
            }
        except Exception as e:
            logger.error(f"Error en Validador LLM: {str(e)}")
            # En caso de error de parseo (Ollama a veces falla con structured output complejo), hacemos fallback
            return {
                "aprobado": "DOY FE" in borrador.upper(),
                "criticas": [f"Error de auditoría AI: {str(e)}. Fallback manual activado."]
            }

    async def validar_escritura_ia(self, borrador: str) -> Dict[str, Any]:
        """
        Usa Ollama para auditar una ESCRITURA completa (LLM-as-a-Judge).
        Busca UIF, AFIP, ITI, Sellos y Registros.
        """
        if self._mock_mode:
            return {"aprobado": True, "criticas": []}

        from pydantic import BaseModel, Field
        class ValidacionEscritura(BaseModel):
            cumple_uif: bool = Field(description="True si menciona origen de fondos o Persona Expuesta Políticamente (UIF/Lavado).")
            cumple_impositivo: bool = Field(description="True si menciona retenciones o exenciones de AFIP, ITI, Ganancias o Sellos.")
            cumple_registral: bool = Field(description="True si menciona certificados de Dominio e Inhibiciones expedidos por el RPI.")
            motivo_rechazo: Optional[str] = Field(description="Si alguno de los anteriores es False, explicar brevemente qué falta. Si todos son True, dejar en blanco.")

        try:
            validador = self._llm.with_structured_output(ValidacionEscritura)
            prompt = f"""
            Eres un Auditor Notarial Experto. Revisa la siguiente Escritura y determina si cumple los requisitos legales:
            1. UIF (Origen de fondos lícitos, Persona Expuesta Políticamente).
            2. IMPOSITIVO (Constancia de retención o exención AFIP, ITI, Ganancias, Sellos).
            3. REGISTRAL (Mención de certificados de Dominio e Inhibición del RPI).
            
            Escritura:
            {borrador}
            """
            
            resultado: ValidacionEscritura = await validador.ainvoke(prompt)
            
            criticas = []
            if not resultado.cumple_uif: criticas.append("Falta cláusula UIF/Origen de Fondos.")
            if not resultado.cumple_impositivo: criticas.append("Falta cláusula Impositiva (AFIP/Sellos/ITI).")
            if not resultado.cumple_registral: criticas.append("Faltan Certificados Registrales (Dominio/Inhibición).")
            if resultado.motivo_rechazo and not criticas: criticas.append(resultado.motivo_rechazo)
            
            aprobado = resultado.cumple_uif and resultado.cumple_impositivo and resultado.cumple_registral
            
            return {
                "aprobado": aprobado,
                "criticas": criticas
            }
        except Exception as e:
            logger.error(f"Error en Validador LLM-as-a-Judge: {str(e)}")
            # Fallback seguro
            return {
                "aprobado": False,
                "criticas": [f"Error de auditoría AI: {str(e)}"]
            }

    def _generar_mock(
        self,
        datos_ofuscados: Dict[str, str],
        tipo_certificacion: TipoDocumentoCertificar,
    ) -> str:
        """Genera texto mock usando plantillas predefinidas."""
        from datetime import datetime
        ahora = datetime.now()
        meses_es = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

        plantilla = _PLANTILLAS_MOCK.get(tipo_certificacion)
        texto = plantilla.format(
            nombre_requirente=datos_ofuscados.get("nombre_requirente", "[NOMBRE_NO_PROVISTO]"),
            dni=datos_ofuscados.get("dni", "[DNI_NO_PROVISTO]"),
            dia=ahora.day,
            mes=meses_es[ahora.month],
            anio=ahora.year,
        )
        return texto

    @property
    def is_mock(self) -> bool:
        return self._mock_mode
        
    def get_llm(self):
        return self._llm
