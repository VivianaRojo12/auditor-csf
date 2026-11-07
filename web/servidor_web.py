"""Servidor estático de la capa de presentación (contenedor separado del servicio).

Sirve la aplicación web e inyecta la URL de la API. No contiene lógica de negocio.
Uso: python web/servidor_web.py [puerto_web] [url_api]
"""
from __future__ import annotations

import http.server
import os
import socketserver
import sys
from functools import partial
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
PUERTO = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("PUERTO_WEB", 8080))
API = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("URL_API", "http://127.0.0.1:8000")


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(RAIZ), **k)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            html = (RAIZ / "index.html").read_text(encoding="utf-8").replace(
                "<script src=\"app.js\"></script>",
                f"<script>window.SENTINELA_API={API!r};</script>\n  <script src=\"app.js\"></script>")
            cuerpo = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)
            return
        super().do_GET()

    def log_message(self, *a):  # silencio
        pass


def main() -> None:
    ejemplo = RAIZ / "politica_ejemplo.md"
    if not ejemplo.exists():
        fuente = RAIZ.parent / "ejemplos" / "politica_hidrosur.md"
        if fuente.exists():
            ejemplo.write_text(fuente.read_text(encoding="utf-8"), encoding="utf-8")
    with socketserver.ThreadingTCPServer(("127.0.0.1", PUERTO), Handler) as s:
        print(f"Aplicación web en http://127.0.0.1:{PUERTO}  (API: {API})")
        s.serve_forever()


if __name__ == "__main__":
    main()
