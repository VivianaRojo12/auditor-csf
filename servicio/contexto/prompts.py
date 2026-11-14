"""C5. Prompts del sistema y esquemas de salida estructurada para cada tarea del modelo."""
from __future__ import annotations

import copy

from servicio.dominio import Seccion

# Cambia cuando cambian los prompts o el esquema; forma parte de la huella de la configuración (llave de caché),
# para que la caché no devuelva análisis hechos con una versión anterior.
VERSION_PROMPTS = "2"

SISTEMA_AUDITOR = (
    "Eres un auditor de seguridad de la información. Analizas una sección de una política o procedimiento "
    "de una organización y la comparas ÚNICAMENTE contra los controles del NIST SP 800-53 que se te entregan "
    "como fuentes. Cada fuente empieza con el identificador del control entre corchetes, por ejemplo [IA-2]. "
    "Reglas: (1) en control_id escribe exactamente ese identificador; (2) en requisito copia la frase del "
    "texto del control que estás evaluando, sin inventarla; (3) el estado y la descripción deben basarse solo "
    "en comparar ese requisito con la sección; (4) si ninguna fuente aplica a la sección, devuelve una lista de "
    "hallazgos vacía. Responde en español."
)

_HALLAZGO = {
    "type": "object",
    "properties": {
        "control_id": {"type": "string"},
        "requisito": {"type": "string"},
        "estado": {"type": "string", "enum": ["cubierto", "parcial", "ausente"]},
        "gravedad": {"type": "string", "enum": ["alta", "media", "baja"]},
        "descripcion": {"type": "string"},
        "evidencia": {"type": "string"},
        "recomendacion": {"type": "string"},
    },
    "required": ["control_id", "requisito", "estado", "gravedad", "descripcion", "recomendacion"],
}

ESQUEMA_ANALISIS = {
    "type": "object",
    "properties": {"resumen": {"type": "string"}, "hallazgos": {"type": "array", "items": _HALLAZGO}},
    "required": ["resumen", "hallazgos"],
}


def esquema_analisis(controles: list[str] | None = None) -> dict:
    """Esquema de análisis restringido a los controles recuperados.

    Con salida estructurada, el servidor de modelos solo permite escribir en control_id uno de los
    controles entregados como fuente, de modo que el modelo no puede citar controles fuera del contexto.
    Sin controles (por ejemplo, la línea base sin RAG) el campo queda libre.
    """
    esquema = copy.deepcopy(ESQUEMA_ANALISIS)
    if controles:
        esquema["properties"]["hallazgos"]["items"]["properties"]["control_id"]["enum"] = list(dict.fromkeys(controles))
    return esquema


ESQUEMA_REFORMULACION = {
    "type": "object",
    "properties": {"consulta": {"type": "string"}, "razon": {"type": "string"}},
    "required": ["consulta"],
}

ESQUEMA_JUEZ = {
    "type": "object",
    "properties": {"puntaje": {"type": "integer"}, "justificacion": {"type": "string"}},
    "required": ["puntaje", "justificacion"],
}


def prompt_analisis(seccion: Seccion, fuentes: str) -> str:
    return (
        f"## Sección a auditar (#{seccion.indice}: {seccion.encabezado()})\n{seccion.texto}\n\n"
        f"## Controles de referencia (fuentes)\n{fuentes or '(no se recuperaron controles aplicables)'}\n\n"
        "## Instrucciones\n"
        "Para cada control de las fuentes que aplique a esta sección, devuelve un hallazgo con:\n"
        "- control_id: el identificador entre corchetes de la fuente (por ejemplo IA-2).\n"
        "- requisito: la frase del texto del control que exige algo relacionado con la sección.\n"
        "- estado: cubierto si la sección cumple ese requisito, parcial si lo menciona pero le falta algo, "
        "ausente si no lo aborda.\n"
        "- gravedad de la brecha (alta, media o baja).\n"
        "- descripcion: qué pide el requisito y qué dice o no dice la sección, en una o dos frases.\n"
        "- evidencia: frase textual de la sección, o vacío si el control está ausente.\n"
        "- recomendacion: redacción concreta que la sección debería incluir para atender el requisito.\n"
        "No incluyas controles que no tengan relación con la sección. Devuelve también un resumen de una frase "
        "de la sección."
    )


def prompt_reformulacion(consulta: str, intento: int) -> str:
    return (
        f"La búsqueda de controles de seguridad para el siguiente texto fue pobre (intento {intento}). "
        "Reescribe la consulta en términos de los objetivos y temas de control de seguridad que trata "
        "(por ejemplo: gestión de cuentas, respaldo, registro de eventos), para mejorar la recuperación.\n\n"
        f"Texto:\n{consulta[:800]}"
    )


def prompt_juez(pregunta: str, respuesta: str, contexto: str) -> str:
    return (
        "Evalúa de 0 a 5 qué tan fiel es la RESPUESTA al CONTEXTO (0 = contradice o inventa, 5 = totalmente "
        "sustentada en el contexto).\n\n"
        f"CONTEXTO:\n{contexto[:2500]}\n\nRESPUESTA:\n{respuesta[:1500]}"
    )
