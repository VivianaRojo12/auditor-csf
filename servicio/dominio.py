"""Tipos de dominio compartidos por todas las capas (núcleo compartido, sin dependencias)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Fragmento:
    """Un fragmento recuperado del corpus de controles."""
    id: str
    texto: str
    metadatos: dict[str, Any]
    puntaje: float = 0.0

    @property
    def control(self) -> str:
        return self.metadatos.get("control", "")

    @property
    def funcion(self) -> str:
        return self.metadatos.get("funcion", "")


@dataclass
class Seccion:
    """Una sección del documento de política que se audita."""
    indice: int
    titulo: str
    texto: str

    def encabezado(self) -> str:
        return self.titulo or f"Sección {self.indice}"


@dataclass
class Documento:
    """Documento de política o procedimiento cargado por el usuario para auditar."""
    nombre: str
    formato: str
    secciones: list[Seccion]
    texto_completo: str = ""
    sha256: str = ""

    @property
    def num_palabras(self) -> int:
        return len(self.texto_completo.split())


@dataclass
class RespuestaModelo:
    texto: str
    modelo: str
    tokens_entrada: int = 0
    tokens_salida: int = 0
    duracion_ms: float = 0.0
    intentos: int = 1
    uso_respaldo: bool = False


@dataclass
class ResultadoGuardrail:
    verificacion: str
    aprobada: bool
    politica: str
    detalle: str = ""


@dataclass
class Hallazgo:
    seccion: int
    seccion_titulo: str
    control_id: str
    funcion: str
    estado: str                 # cubierto | parcial | ausente
    gravedad: str               # alta | media | baja
    descripcion: str
    evidencia: str              # cita del documento del usuario
    recomendacion: str
    fuente: dict[str, Any] = field(default_factory=dict)  # control del corpus + puntaje
    requisito: str = ""         # frase del control que sustenta el hallazgo


def normalizar_control(texto: str) -> str:
    """Identificador canónico de un control: 'ia-2', 'IA 2', '[IA-2]' o 'IA-2 Identification...' -> 'IA-2'."""
    m = re.search(r"\b([A-Za-z]{2})\s*-?\s*(\d{1,2})\b", str(texto))
    return f"{m.group(1).upper()}-{int(m.group(2))}" if m else str(texto).strip().upper()


class ErrorModelo(Exception):
    """El gateway no pudo obtener respuesta de ningún modelo."""
