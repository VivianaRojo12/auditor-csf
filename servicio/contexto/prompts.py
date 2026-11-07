"""C5. Prompts del sistema y esquemas de salida estructurada para cada tarea del modelo."""
from __future__ import annotations

from servicio.dominio import Seccion

SISTEMA_AUDITOR = (
    "Eres un auditor de seguridad de la información. Analizas una sección de una política o procedimiento "
    "de una organización y la comparas ÚNICAMENTE contra los controles del NIST SP 800-53 que se te entregan "
    "como fuentes. Para cada control relevante determinas si la sección lo cubre, lo cubre parcialmente o no "
    "lo menciona, con qué gravedad y con qué evidencia textual. No inventes controles ni cites fuentes que no "
    "estén en la lista. Si ninguna fuente aplica a la sección, devuelve una lista de hallazgos vacía. "
    "Cada hallazgo debe citar la etiqueta de la fuente (F1, F2, ...) de la que proviene el control. "
    "Responde en español."
)

ESQUEMA_ANALISIS = {
    "type": "object",
    "properties": {
        "resumen": {"type": "string"},
        "hallazgos": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "control_id": {"type": "string"},
                    "estado": {"type": "string", "enum": ["cubierto", "parcial", "ausente"]},
                    "gravedad": {"type": "string", "enum": ["alta", "media", "baja"]},
                    "descripcion": {"type": "string"},
                    "evidencia": {"type": "string"},
                    "recomendacion": {"type": "string"},
                    "fuente": {"type": "string"},
                },
                "required": ["control_id", "estado", "gravedad", "descripcion", "recomendacion", "fuente"],
            },
        },
    },
    "required": ["resumen", "hallazgos"],
}

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
        "Identifica los controles de las fuentes que aplican a esta sección. Para cada uno, indica el estado "
        "(cubierto/parcial/ausente), la gravedad de la brecha, una descripción breve, la evidencia (frase textual "
        "de la sección, o vacío si el control está ausente), una recomendación de redacción corregida y la "
        "etiqueta de la fuente. Devuelve también un resumen de una frase de la sección."
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
