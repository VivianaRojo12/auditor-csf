"""Raíz de composición: construye y conecta todas las capas a partir de la configuración.

Es el único lugar donde se eligen los adaptadores concretos (Ollama o simulado, Chroma o memoria).
Las capas superiores reciben sus dependencias por su interfaz, no las crean.
"""
from __future__ import annotations

from pathlib import Path

from servicio.cache.cache import CacheConsultas
from servicio.config import Configuracion, obtener
from servicio.contexto.rag import ConstructorContexto
from servicio.datos.ollama import AdaptadorOllama
from servicio.datos.simulado import AdaptadorSimulado
from servicio.datos.sqlite import (AlmacenCacheSQLite, AlmacenDocumentosSQLite, AlmacenEventosSQLite,
                                   AlmacenRetroalimentacionSQLite)
from servicio.datos.vectorial import VectorialChroma, VectorialMemoria
from servicio.modelos.enrutador import Enrutador
from servicio.modelos.gateway import GatewayModelos
from servicio.observabilidad.trazas import observador
from servicio.orquestacion.orquestador import Orquestador
from servicio.retroalimentacion.registro import ServicioRetroalimentacion

RAIZ = Path(__file__).resolve().parent.parent


class Contenedor:
    def __init__(self, conf: Configuracion | None = None) -> None:
        self.conf = conf or obtener()
        d = self.conf.dir_datos

        # C7 adaptadores
        if self.conf.proveedor_modelos == "simulado":
            self.servidor = AdaptadorSimulado()
        else:
            self.servidor = AdaptadorOllama(self.conf.url_ollama)
        if self.conf.base_vectorial["tipo"] == "memoria":
            self.base = VectorialMemoria()
        else:
            self.base = VectorialChroma(d / "chroma", self.conf.base_vectorial["coleccion"])
        self.docs = AlmacenDocumentosSQLite(d)
        self.cache_almacen = AlmacenCacheSQLite(d)
        self.eventos = AlmacenEventosSQLite(d)
        self.retro_almacen = AlmacenRetroalimentacionSQLite(d)

        # T1 observabilidad
        observador.configurar(self.eventos, d / "bitacoras")

        # capas superiores
        self.contexto = ConstructorContexto(self.conf, self.servidor, self.base)
        self.enrutador = Enrutador(self.conf.enrutador["umbral_complejidad"])
        self.gateway = GatewayModelos(self.servidor, self.conf.modelos)
        self.cache = CacheConsultas(self.cache_almacen, self.conf.cache, self.conf.huella())
        self.orquestador = Orquestador(self.conf, self.contexto, self.enrutador, self.gateway, self.cache)
        self.retro = ServicioRetroalimentacion(self.retro_almacen)

    def version_corpus(self) -> str:
        return self.docs.version_corpus()
