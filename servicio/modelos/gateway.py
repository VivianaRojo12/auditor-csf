"""C6. Gateway de modelos: interfaz única hacia todos los modelos de lenguaje.

Aplica tiempo límite, reintentos con espera creciente, modelo de respaldo y registro de uso por llamada.
"""
from __future__ import annotations

import time
from typing import Any

from servicio.config import ConfModelos
from servicio.datos.interfaces import ServidorModelos
from servicio.dominio import ErrorModelo, RespuestaModelo
from servicio.observabilidad.trazas import observador


class GatewayModelos:
    def __init__(self, servidor: ServidorModelos, conf: ConfModelos) -> None:
        self._servidor = servidor
        self._conf = conf

    def modelo_de_ruta(self, ruta: str) -> str:
        return self._conf.rutas[ruta].modelo

    def _opciones(self, max_tokens: int | None) -> dict[str, Any]:
        return {"temperature": self._conf.temperatura, "num_ctx": self._conf.num_ctx,
                "num_predict": max_tokens or self._conf.max_tokens_salida}

    def _llamar(self, modelo: str, mensajes: list[dict[str, str]], esquema: dict | None,
                tiempo_limite_s: float, max_tokens: int | None) -> RespuestaModelo:
        ultimo_error: Exception | None = None
        for intento in range(1, self._conf.reintentos + 2):
            inicio = time.perf_counter()
            try:
                r = self._servidor.generar(modelo, mensajes, esquema, tiempo_limite_s, self._opciones(max_tokens))
                r.intentos = intento
                observador.registrar("modelos", "llamada", (time.perf_counter() - inicio) * 1000, modelo=modelo,
                                     intento=intento, tokens_entrada=r.tokens_entrada, tokens_salida=r.tokens_salida)
                return r
            except Exception as error:  # el gateway traduce cualquier falla del servidor a reintento o respaldo
                ultimo_error = error
                observador.registrar("modelos", "error", (time.perf_counter() - inicio) * 1000, modelo=modelo,
                                     intento=intento, error=f"{type(error).__name__}: {error}"[:300])
                if intento <= self._conf.reintentos and not isinstance(error, TimeoutError) \
                        and "Timeout" not in type(error).__name__:
                    time.sleep(0.5 * intento)
                else:
                    break
        raise ErrorModelo(str(ultimo_error))

    def generar(self, mensajes: list[dict[str, str]], *, ruta: str | None = None, modelo: str | None = None,
                esquema: dict | None = None, max_tokens: int | None = None, usar_respaldo: bool = True) -> RespuestaModelo:
        elegido = modelo or self.modelo_de_ruta(ruta or "simple")
        limite = self._conf.rutas[ruta].tiempo_limite_s if ruta in self._conf.rutas else \
            max(r.tiempo_limite_s for r in self._conf.rutas.values())
        try:
            return self._llamar(elegido, mensajes, esquema, limite, max_tokens)
        except ErrorModelo:
            if not usar_respaldo or elegido == self._conf.respaldo:
                raise
            observador.registrar("modelos", "respaldo", modelo_original=elegido, modelo_respaldo=self._conf.respaldo)
            r = self._llamar(self._conf.respaldo, mensajes, esquema, limite, max_tokens)
            r.uso_respaldo = True
            return r
