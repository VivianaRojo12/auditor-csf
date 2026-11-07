"""Punto de entrada del servicio. Uso: python -m servicio.main  (o uvicorn servicio.main:app)."""
from __future__ import annotations

import uvicorn

from servicio.api.app import crear_app
from servicio.config import obtener
from servicio.contenedor import Contenedor

contenedor = Contenedor()
app = crear_app(contenedor)


def main() -> None:
    conf = obtener()
    uvicorn.run(app, host=conf.servicio.host, port=conf.servicio.puerto, log_level="warning")


if __name__ == "__main__":
    main()
