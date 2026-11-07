"""C1. Esquemas Pydantic de entrada y salida de la API."""
from __future__ import annotations

from pydantic import BaseModel, Field


class Retroalimentacion(BaseModel):
    traza_id: str
    util: bool
    comentario: str | None = Field(default=None, max_length=1000)
    origen: str = "usuario"


class Pregunta(BaseModel):
    pregunta: str = Field(min_length=3, max_length=2000)


class RespuestaDocumento(BaseModel):
    id: str
    nombre: str
    fragmentos: int
