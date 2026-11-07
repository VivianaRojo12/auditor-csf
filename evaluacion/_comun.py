"""Utilidades compartidas por los scripts de evaluación."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "evaluacion" / "datos"
RESULTADOS = RAIZ / "evaluacion" / "resultados"


def cargar(nombre: str) -> dict:
    return json.loads((DATOS / nombre).read_text(encoding="utf-8"))


def guardar(nombre: str, datos: dict) -> Path:
    RESULTADOS.mkdir(parents=True, exist_ok=True)
    ruta = RESULTADOS / nombre
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    return ruta


def cronometrar(fn: Callable, *a, **k) -> tuple[Any, float]:
    inicio = time.perf_counter()
    r = fn(*a, **k)
    return r, (time.perf_counter() - inicio) * 1000


def servidor_de(conf):
    """Devuelve el adaptador de modelos según la configuración (Ollama o simulado)."""
    if conf.proveedor_modelos == "simulado":
        from servicio.datos.simulado import AdaptadorSimulado
        return AdaptadorSimulado()
    from servicio.datos.ollama import AdaptadorOllama
    return AdaptadorOllama(conf.url_ollama)


def familia_de(control: str) -> str:
    return control.split("-")[0].upper()


def acierto_en_k(recuperados: list[str], esperados_familia: list[str], k: int) -> bool:
    fams = {familia_de(c) for c in recuperados[:k]}
    return any(f in fams for f in esperados_familia)
