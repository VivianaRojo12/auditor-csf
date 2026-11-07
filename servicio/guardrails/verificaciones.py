"""C3. Guardrails de entrada y salida.

Entrada (3 verificaciones):
  - documento_valido: tamaño y contenido textual dentro de límites.
  - datos_personales: detecta datos personales (CURP, RFC, correos, teléfonos) y los anonimiza antes de enviarlos al modelo.
  - inyeccion_instrucciones: detecta intentos de inyección de instrucciones en el texto del documento.
Salida (3 verificaciones):
  - esquema_valido: la respuesta del modelo es el JSON esperado.
  - fuentes_validas: cada hallazgo cita una fuente realmente recuperada (apego al contexto).
  - sin_datos_personales: la respuesta no filtra datos personales.

Cada verificación declara su política ante la falla: bloquear, anonimizar, reintentar o mensaje seguro.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from servicio.dominio import ResultadoGuardrail
from servicio.observabilidad.trazas import observador

PATRONES_PERSONALES: list[tuple[str, str, re.Pattern]] = [
    ("CURP", "[CURP]", re.compile(r"\b[A-Z][AEIOUX][A-Z]{2}\d{6}[HM][A-Z]{5}[0-9A-Z]\d\b")),
    ("RFC", "[RFC]", re.compile(r"\b[A-ZÑ&]{3,4}\d{6}[0-9A-Z]{3}\b")),
    ("correo", "[CORREO]", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    ("teléfono", "[TELÉFONO]", re.compile(r"\b(?:\+?52\s?)?(?:\d[\s-]?){10}\b")),
]

PATRONES_INYECCION = [
    re.compile(r"ignor[ae]\s+(todas\s+)?(las\s+)?(instruccion|indicacion|regla)", re.I),
    re.compile(r"olvida\s+(todo|lo anterior|las instrucciones)", re.I),
    re.compile(r"\b(act[úu]a|comp[óo]rtate)\s+como\b", re.I),
    re.compile(r"(nuevas?\s+instruccion|a partir de ahora eres|system prompt|prompt del sistema)", re.I),
    re.compile(r"(no\s+(audites|evalúes|reportes)|marca\s+todo\s+como\s+(cubierto|conforme))", re.I),
    re.compile(r"disregard\s+(the\s+)?(above|previous)|ignore\s+(all\s+)?previous", re.I),
]


@dataclass
class ResultadoEntrada:
    aprobada: bool
    texto_saneado: str
    resultados: list[ResultadoGuardrail]
    mensaje_seguro: str | None = None


def _registrar(r: ResultadoGuardrail) -> ResultadoGuardrail:
    observador.registrar("guardrails", "verificacion", verificacion=r.verificacion, aprobada=r.aprobada,
                         politica=r.politica, detalle=r.detalle[:160])
    return r


def verificar_entrada(texto: str, conf: dict) -> ResultadoEntrada:
    resultados: list[ResultadoGuardrail] = []

    # 1. documento válido (política: bloquear)
    n = len(texto)
    valido = 20 <= n <= conf["max_bytes"]
    resultados.append(_registrar(ResultadoGuardrail(
        "documento_valido", valido, "bloquear",
        "" if valido else f"longitud {n} fuera del rango permitido")))
    if not valido:
        return ResultadoEntrada(False, texto, resultados,
                                "El documento está vacío o excede el tamaño permitido para la auditoría.")

    # 2. inyección de instrucciones (política: bloquear)
    coincidencias = [p.pattern for p in PATRONES_INYECCION if p.search(texto)]
    sin_inyeccion = not coincidencias
    resultados.append(_registrar(ResultadoGuardrail(
        "inyeccion_instrucciones", sin_inyeccion, "bloquear",
        "" if sin_inyeccion else f"{len(coincidencias)} patrón(es) sospechoso(s)")))
    if not sin_inyeccion:
        return ResultadoEntrada(False, texto, resultados,
                                "El documento contiene instrucciones dirigidas al sistema de IA. Por seguridad, "
                                "la auditoría se detuvo. Revisa el documento y elimina ese contenido.")

    # 3. datos personales (política: anonimizar y continuar)
    saneado, encontrados = anonimizar(texto)
    resultados.append(_registrar(ResultadoGuardrail(
        "datos_personales", True, "anonimizar",
        f"anonimizados: {', '.join(encontrados)}" if encontrados else "sin datos personales detectados")))
    return ResultadoEntrada(True, saneado, resultados)


def anonimizar(texto: str) -> tuple[str, list[str]]:
    encontrados: list[str] = []
    for nombre, reemplazo, patron in PATRONES_PERSONALES:
        if patron.search(texto):
            texto = patron.sub(reemplazo, texto)
            encontrados.append(nombre)
    return texto, encontrados


def verificar_salida(datos: dict | None, etiquetas_validas: set[str]) -> tuple[bool, list[ResultadoGuardrail], str]:
    resultados: list[ResultadoGuardrail] = []

    # 1. esquema válido (política: reintentar)
    valido = isinstance(datos, dict) and isinstance(datos.get("hallazgos"), list)
    resultados.append(_registrar(ResultadoGuardrail(
        "esquema_valido", valido, "reintentar", "" if valido else "la respuesta no tiene la forma esperada")))
    if not valido:
        return False, resultados, "reintentar"

    # 2. fuentes válidas / apego al contexto (política: descartar hallazgo sin fuente válida)
    hallazgos = datos["hallazgos"]
    invalidos = [h for h in hallazgos if h.get("fuente") not in etiquetas_validas]
    apego = not invalidos
    if invalidos:
        datos["hallazgos"] = [h for h in hallazgos if h.get("fuente") in etiquetas_validas]
    resultados.append(_registrar(ResultadoGuardrail(
        "fuentes_validas", apego, "descartar_sin_fuente",
        "" if apego else f"{len(invalidos)} hallazgo(s) sin fuente válida, descartados")))

    # 3. sin datos personales en la salida (política: anonimizar)
    serial = str(datos)
    _, filtrados = anonimizar(serial)
    sin_pii = not filtrados
    if not sin_pii:
        for h in datos["hallazgos"]:
            for campo in ("descripcion", "evidencia", "recomendacion"):
                if h.get(campo):
                    h[campo] = anonimizar(h[campo])[0]
    resultados.append(_registrar(ResultadoGuardrail(
        "sin_datos_personales", sin_pii, "anonimizar",
        "" if sin_pii else f"anonimizados en la salida: {', '.join(filtrados)}")))
    return True, resultados, "aprobada"
