"""C1. Esquemas Pydantic de entrada y salida de la API."""
from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


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


class AciertosFamilia(BaseModel):
    aciertos: int = Field(ge=0, le=20)
    total: int = Field(ge=1, le=20)

    @model_validator(mode="after")
    def _coherente(self):
        if self.aciertos > self.total:
            raise ValueError("aciertos no puede ser mayor que total")
        return self


class ResultadoPractica(BaseModel):
    """Resultado anónimo de un cuestionario: solo familias y aciertos, sin datos de la persona."""
    familia: str | None = Field(default=None, pattern=r"^[A-Za-z]{2}$")   # tema elegido; None = todas
    por_familia: dict[str, AciertosFamilia] = Field(min_length=1, max_length=20)
