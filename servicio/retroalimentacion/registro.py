"""T2. Retroalimentación del usuario: registra la opinión sobre cada resultado y la liga con su traza."""
from __future__ import annotations

from typing import Any, Protocol

from servicio.observabilidad.trazas import observador


class AlmacenRetroalimentacion(Protocol):
    def guardar_retroalimentacion(self, traza_id: str, util: bool, comentario: str | None, origen: str) -> int: ...
    def listar_retroalimentacion(self) -> list[dict[str, Any]]: ...


class TrazaInexistente(Exception):
    pass


class ServicioRetroalimentacion:
    def __init__(self, almacen: AlmacenRetroalimentacion) -> None:
        self._almacen = almacen

    def registrar(self, traza_id: str, util: bool, comentario: str | None = None, origen: str = "usuario") -> int:
        if observador.almacen is not None and not observador.almacen.eventos_de_traza(traza_id):
            raise TrazaInexistente(traza_id)
        identificador = self._almacen.guardar_retroalimentacion(traza_id, util, comentario, origen)
        observador.registrar("retroalimentacion", "registrada", traza_original=traza_id, util=util, origen=origen)
        return identificador

    def resumen(self) -> dict[str, Any]:
        registros = self._almacen.listar_retroalimentacion()
        utiles = sum(1 for r in registros if r["util"])
        return {
            "total": len(registros),
            "utiles": utiles,
            "no_utiles": len(registros) - utiles,
            "proporcion_util": round(utiles / len(registros), 3) if registros else None,
            "ultimos_comentarios": [
                {"traza_id": r["traza_id"], "util": bool(r["util"]), "comentario": r["comentario"]}
                for r in registros[-5:] if r["comentario"]
            ],
        }
