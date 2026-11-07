"""Carga de la configuración del servicio desde config.yaml."""
from __future__ import annotations

import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

RAIZ = Path(__file__).resolve().parent.parent


class Ruta(BaseModel):
    modelo: str
    tiempo_limite_s: float = 240


class ConfModelos(BaseModel):
    rutas: dict[str, Ruta]
    respaldo: str
    modelo_reformulacion: str
    reintentos: int = 1
    num_ctx: int = 8192
    temperatura: float = 0.1
    max_tokens_salida: int = 900


class ConfEmbeddings(BaseModel):
    modelo: str
    prefijos: dict[str, dict[str, str]] = Field(default_factory=dict)
    lote: int = 32

    def prefijo(self, tipo: Literal["consulta", "documento"], modelo: str | None = None) -> str:
        return self.prefijos.get(modelo or self.modelo, {}).get(tipo, "")


class ConfServicio(BaseModel):
    host: str = "127.0.0.1"
    puerto: int = 8000
    directorio_datos: str = "datos_runtime"
    origenes_web: list[str] = Field(default_factory=list)


class Configuracion(BaseModel):
    servicio: ConfServicio
    proveedor_modelos: Literal["ollama", "simulado"] = "ollama"
    url_ollama: str = "http://127.0.0.1:11434"
    modelos: ConfModelos
    embeddings: ConfEmbeddings
    base_vectorial: dict
    fragmentacion: dict
    recuperacion: dict
    agente: dict
    cache: dict
    enrutador: dict
    guardrails: dict

    @property
    def dir_datos(self) -> Path:
        ruta = Path(self.servicio.directorio_datos)
        if not ruta.is_absolute():
            ruta = RAIZ / ruta
        ruta.mkdir(parents=True, exist_ok=True)
        return ruta

    def huella(self) -> str:
        """Huella de los parámetros que cambian el resultado de un análisis (forma parte de la llave de caché)."""
        relevante = {
            "modelos": self.modelos.model_dump(),
            "embeddings": self.embeddings.modelo,
            "fragmentacion": self.fragmentacion,
            "recuperacion": self.recuperacion,
            "agente": self.agente,
        }
        return hashlib.sha256(json.dumps(relevante, sort_keys=True).encode()).hexdigest()[:12]


def cargar(ruta: str | Path | None = None) -> Configuracion:
    ruta = Path(ruta or os.environ.get("SENTINELA_CONFIG", RAIZ / "config.yaml"))
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    if os.environ.get("SENTINELA_PROVEEDOR"):
        datos["proveedor_modelos"] = os.environ["SENTINELA_PROVEEDOR"]
    if os.environ.get("SENTINELA_DATOS"):
        datos["servicio"]["directorio_datos"] = os.environ["SENTINELA_DATOS"]
    if os.environ.get("SENTINELA_VECTORIAL"):
        datos["base_vectorial"]["tipo"] = os.environ["SENTINELA_VECTORIAL"]
    return Configuracion(**datos)


@lru_cache
def obtener() -> Configuracion:
    return cargar()
