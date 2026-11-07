"""C2. Ensamblado del informe de auditoría a partir de los resultados por sección.

Agrupa los hallazgos por función del CSF 2.0 y calcula un puntaje de cobertura por función
(no es una calificación oficial; es un indicador interno de la auditoría).
"""
from __future__ import annotations

from typing import Any

from servicio.csf import FUNCIONES, nombre_funcion
from servicio.orquestacion.orquestador import ResultadoSeccion

PESO_ESTADO = {"cubierto": 1.0, "parcial": 0.5, "ausente": 0.0}
PESO_GRAVEDAD = {"alta": 3, "media": 2, "baja": 1}


def ensamblar(nombre_documento: str, resultados: list[ResultadoSeccion], traza_id: str) -> dict[str, Any]:
    hallazgos: list[dict] = []
    for r in resultados:
        for h in r.hallazgos:
            hallazgos.append(h.__dict__)

    por_funcion: dict[str, dict[str, Any]] = {}
    for codigo in FUNCIONES:
        rel = [h for h in hallazgos if h["funcion"] == codigo]
        if not rel:
            continue
        cobertura = sum(PESO_ESTADO.get(h["estado"], 0) for h in rel) / len(rel)
        por_funcion[codigo] = {
            "funcion": codigo, "nombre": nombre_funcion(codigo), "hallazgos": len(rel),
            "cubierto": sum(1 for h in rel if h["estado"] == "cubierto"),
            "parcial": sum(1 for h in rel if h["estado"] == "parcial"),
            "ausente": sum(1 for h in rel if h["estado"] == "ausente"),
            "cobertura": round(cobertura, 2),
        }

    graves = [h for h in hallazgos if h["estado"] != "cubierto" and h["gravedad"] == "alta"]
    brechas = [h for h in hallazgos if h["estado"] != "cubierto"]
    secciones_bloqueadas = [r.seccion for r in resultados if r.bloqueada]
    return {
        "documento": nombre_documento,
        "traza_id": traza_id,
        "resumen": {
            "secciones_analizadas": len([r for r in resultados if not r.bloqueada]),
            "secciones_bloqueadas": secciones_bloqueadas,
            "hallazgos_totales": len(hallazgos),
            "brechas": len(brechas),
            "brechas_graves": len(graves),
            "controles_citados": sorted({h["control_id"] for h in hallazgos if h["control_id"]}),
        },
        "por_funcion": list(por_funcion.values()),
        "prioridades": sorted(
            brechas, key=lambda h: (-PESO_GRAVEDAD.get(h["gravedad"], 0),
                                    0 if h["estado"] == "ausente" else 1))[:10],
        "hallazgos": hallazgos,
        "secciones": [
            {"seccion": r.seccion, "titulo": r.titulo, "resumen": r.resumen, "modelo": r.modelo, "ruta": r.ruta,
             "cache": r.cache, "iteraciones_agente": r.iteraciones_agente, "bloqueada": r.bloqueada,
             "mensaje": r.mensaje, "hallazgos": len(r.hallazgos), "fuentes": r.fuentes}
            for r in resultados
        ],
    }
