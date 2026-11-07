"""T1. Observabilidad: identificador de traza, bitácoras estructuradas por capa y registro de métricas.

Capa transversal: cualquier capa puede usarla. El almacén de eventos se inyecta desde la raíz de
composición (servicio/main.py), de modo que esta capa no depende de ningún adaptador concreto.
"""
from __future__ import annotations

import contextvars
import json
import logging
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Protocol

_traza_actual: contextvars.ContextVar[str | None] = contextvars.ContextVar("traza_id", default=None)


class AlmacenEventos(Protocol):
    def guardar_evento(self, evento: dict[str, Any]) -> None: ...
    def eventos_de_traza(self, traza_id: str) -> list[dict[str, Any]]: ...
    def resumen_metricas(self) -> dict[str, Any]: ...


class _FormatoJSON(logging.Formatter):
    def format(self, registro: logging.LogRecord) -> str:
        base = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(registro.created)),
            "nivel": registro.levelname,
            "capa": registro.name.removeprefix("sentinela."),
            "mensaje": registro.getMessage(),
            "traza_id": _traza_actual.get(),
        }
        extra = getattr(registro, "datos", None)
        if extra:
            base["datos"] = extra
        return json.dumps(base, ensure_ascii=False, default=str)


class Observador:
    def __init__(self) -> None:
        self._almacen: AlmacenEventos | None = None

    def configurar(self, almacen: AlmacenEventos, directorio_bitacoras: Path) -> None:
        self._almacen = almacen
        directorio_bitacoras.mkdir(parents=True, exist_ok=True)
        raiz = logging.getLogger("sentinela")
        raiz.setLevel(logging.INFO)
        raiz.handlers.clear()
        archivo = logging.FileHandler(directorio_bitacoras / "sentinela.jsonl", encoding="utf-8")
        archivo.setFormatter(_FormatoJSON())
        consola = logging.StreamHandler()
        consola.setFormatter(_FormatoJSON())
        raiz.addHandler(archivo)
        raiz.addHandler(consola)
        raiz.propagate = False

    @property
    def almacen(self) -> AlmacenEventos | None:
        return self._almacen

    @staticmethod
    def nueva_traza() -> str:
        traza = uuid.uuid4().hex[:12]
        _traza_actual.set(traza)
        return traza

    @staticmethod
    def traza() -> str | None:
        return _traza_actual.get()

    def registrar(self, capa: str, evento: str, duracion_ms: float | None = None, **datos: Any) -> None:
        registro = {
            "traza_id": _traza_actual.get(),
            "capa": capa,
            "evento": evento,
            "duracion_ms": round(duracion_ms, 2) if duracion_ms is not None else None,
            "datos": datos,
            "ts": time.time(),
        }
        logging.getLogger(f"sentinela.{capa}").info(evento, extra={"datos": {**datos, "duracion_ms": registro["duracion_ms"]}})
        if self._almacen is not None:
            self._almacen.guardar_evento(registro)

    @contextmanager
    def medir(self, capa: str, evento: str, **datos: Any):
        inicio = time.perf_counter()
        extra: dict[str, Any] = {}
        try:
            yield extra
        finally:
            self.registrar(capa, evento, (time.perf_counter() - inicio) * 1000, **datos, **extra)


observador = Observador()
