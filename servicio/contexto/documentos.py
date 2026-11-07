"""C5. Lectura y fragmentación de los documentos de política que se auditan.

Acepta PDF, DOCX, Markdown y texto plano. Divide el documento en secciones por sus encabezados
(para auditar sección por sección) y, para el indexado del corpus, en fragmentos con solapamiento.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from servicio.dominio import Documento, Fragmento, Seccion

ENCABEZADO = re.compile(
    r"^\s*(?:#{1,6}\s+.+"                         # Markdown
    r"|\d+(?:\.\d+)*\.?\s+[^\n]{3,80}"            # 1.  /  2.3  numerado
    r"|[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9 ,\-/]{4,70})\s*$" # TÍTULO EN MAYÚSCULAS
)


def _leer_crudo(ruta: Path) -> tuple[str, str]:
    ext = ruta.suffix.lower().lstrip(".")
    if ext == "pdf":
        from pypdf import PdfReader
        texto = "\n".join((p.extract_text() or "") for p in PdfReader(str(ruta)).pages)
        return texto, "pdf"
    if ext in {"docx", "dotx"}:
        import docx
        return "\n".join(p.text for p in docx.Document(str(ruta)).paragraphs), "docx"
    if ext in {"md", "markdown"}:
        return ruta.read_text(encoding="utf-8", errors="ignore"), "md"
    return ruta.read_text(encoding="utf-8", errors="ignore"), "txt"


def _limpiar(texto: str) -> str:
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")
    texto = re.sub(r"[ \t]+", " ", texto)
    return re.sub(r"\n{3,}", "\n\n", texto).strip()


def _secciones(texto: str) -> list[Seccion]:
    lineas = texto.split("\n")
    secciones: list[Seccion] = []
    titulo, cuerpo = "Preámbulo", []
    for linea in lineas:
        if ENCABEZADO.match(linea) and len(linea.strip()) <= 80:
            if cuerpo and "".join(cuerpo).strip():
                secciones.append(Seccion(len(secciones) + 1, titulo, "\n".join(cuerpo).strip()))
                cuerpo = []
            titulo = re.sub(r"^#{1,6}\s+", "", linea.strip())
        else:
            cuerpo.append(linea)
    if cuerpo and "".join(cuerpo).strip():
        secciones.append(Seccion(len(secciones) + 1, titulo, "\n".join(cuerpo).strip()))
    if not secciones:
        secciones = [Seccion(1, "Documento", texto.strip())]
    return secciones


def leer_documento(ruta: str | Path, nombre: str | None = None, contenido: bytes | None = None) -> Documento:
    ruta = Path(ruta)
    if contenido is not None:
        ruta.write_bytes(contenido)
    crudo, formato = _leer_crudo(ruta)
    texto = _limpiar(crudo)
    sha = hashlib.sha256((contenido if contenido is not None else ruta.read_bytes())).hexdigest()
    return Documento(nombre=nombre or ruta.name, formato=formato, secciones=_secciones(texto),
                     texto_completo=texto, sha256=sha)


def fragmentar_texto(texto: str, tamano: int, solapamiento: int) -> list[str]:
    texto = _limpiar(texto)
    if len(texto) <= tamano:
        return [texto] if texto else []
    fragmentos, inicio = [], 0
    while inicio < len(texto):
        fin = inicio + tamano
        corte = texto.rfind("\n", inicio + tamano // 2, fin)
        if corte == -1:
            corte = texto.rfind(" ", inicio + tamano // 2, fin)
        fin = corte if corte != -1 and fin < len(texto) else fin
        bloque = texto[inicio:fin].strip()
        if bloque:
            fragmentos.append(bloque)
        if fin >= len(texto):
            break
        inicio = max(fin - solapamiento, inicio + 1)
    return fragmentos


def fragmentar_control(ruta: Path, tamano: int, solapamiento: int) -> list[Fragmento]:
    """Fragmenta un archivo de control del corpus conservando sus metadatos de encabezado."""
    texto = ruta.read_text(encoding="utf-8")
    meta: dict[str, str] = {"doc_id": f"control:{ruta.stem}", "documento": ruta.stem, "tipo": "control"}
    for linea in texto.splitlines():
        if linea.startswith("- Control:"):
            meta["control"] = linea.split(":", 1)[1].strip()
        elif linea.startswith("- Función CSF 2.0:"):
            meta["funcion"] = linea.split(":", 1)[1].strip().split(" ")[0]
        elif linea.startswith("- Familia:"):
            meta["familia"] = linea.split(":", 1)[1].strip()
    titulo = texto.splitlines()[0].lstrip("# ").strip()
    meta["titulo"] = titulo
    fragmentos = []
    for i, bloque in enumerate(fragmentar_texto(texto, tamano, solapamiento)):
        fragmentos.append(Fragmento(id=f"{ruta.stem}::{i}", texto=bloque, metadatos={**meta, "parte": i}))
    return fragmentos
