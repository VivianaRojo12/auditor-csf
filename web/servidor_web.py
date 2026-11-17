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
DEMOS = RAIZ.parent / "ejemplos" / "demo"
TIPOS = {".md": "text/markdown; charset=utf-8", ".txt": "text/plain; charset=utf-8", ".pdf": "application/pdf",
         ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(RAIZ), **k)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            html = (RAIZ / "index.html").read_text(encoding="utf-8").replace(
                "<script src=\"app.js\"></script>",
                f"<script>window.AUDITOR_API={API!r};</script>\n  <script src=\"app.js\"></script>")
            cuerpo = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(cuerpo)))
            self.end_headers()
            self.wfile.write(cuerpo)
            return
        if self.path.startswith("/demo/"):
            self._servir_demo(self.path[len("/demo/"):])
            return
        super().do_GET()

    def _servir_demo(self, nombre: str) -> None:
        """Archivos de demostración de ejemplos/demo (solo los que existen en esa carpeta, sin subrutas)."""
        disponibles = {p.name: p for p in DEMOS.glob("*") if p.is_file()} if DEMOS.is_dir() else {}
        archivo = disponibles.get(nombre)
        if archivo is None:
            self.send_error(404, "Demostración no encontrada")
            return
        cuerpo = archivo.read_bytes()
        tipo = TIPOS.get(archivo.suffix.lower(), "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

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
