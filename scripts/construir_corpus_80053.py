"""Construye el corpus de controles a partir del catálogo oficial NIST SP 800-53 Rev. 5 (OSCAL JSON).

Fuente: https://github.com/usnistgov/oscal-content (dominio público, CC0 1.0).
Genera un Markdown por control base (se omiten las mejoras "(n)" para mantener el corpus enfocado),
con el enunciado, la guía y la función del CSF 2.0 a la que se asocia la familia.

Uso: python scripts/construir_corpus_80053.py RUTA/NIST_SP-800-53_rev5_catalog.json corpus/controles
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from servicio.csf import NOMBRE_FAMILIA, funcion_de_control, nombre_funcion  # noqa: E402


def texto_parte(parte: dict, params: dict[str, str], nivel: int = 0) -> str:
    lineas: list[str] = []
    prosa = parte.get("prose")
    if prosa:
        prosa = re.sub(r"\{\{\s*insert:\s*param,\s*([\w.-]+)\s*\}\}",
                       lambda m: params.get(m.group(1), "[parámetro asignado por la organización]"), prosa)
        etiqueta = next((p["value"] for p in parte.get("props", []) if p.get("name") == "label"), None)
        viñeta = f"{'  ' * nivel}{'- ' if nivel else ''}"
        lineas.append(f"{viñeta}{etiqueta + ' ' if etiqueta else ''}{prosa}".rstrip())
    for sub in parte.get("parts", []):
        if sub.get("name") in {"statement", "item", "guidance"}:
            lineas.append(texto_parte(sub, params, nivel + 1 if parte.get("name") in {"statement", "item"} else nivel))
    return "\n".join(l for l in lineas if l.strip())


def params_de_control(control: dict) -> dict[str, str]:
    salida: dict[str, str] = {}
    for p in control.get("params", []):
        etiqueta = p.get("label")
        if not etiqueta and "select" in p:
            opciones = [c.get("value", "") if isinstance(c, dict) else str(c)
                        for c in p["select"].get("choice", [])]
            etiqueta = " / ".join(o for o in opciones if o)
        salida[p["id"]] = f"[{etiqueta}]" if etiqueta else "[parámetro asignado por la organización]"
    return salida


def main(origen: str, destino: str) -> None:
    catalogo = json.loads(Path(origen).read_text(encoding="utf-8"))["catalog"]
    version = catalogo.get("metadata", {}).get("version", "Rev. 5")
    salida = Path(destino)
    salida.mkdir(parents=True, exist_ok=True)
    total = 0
    indice: list[dict] = []
    for familia in catalogo.get("groups", []):
        fam_id = familia["id"]
        for control in familia.get("controls", []):
            cid = control["id"]
            if re.search(r"\.\d+$|-\d+\.\d+$", cid) or "(" in cid:
                continue  # omitir mejoras de control
            params = params_de_control(control)
            partes = control.get("parts", [])
            enunciado = next((texto_parte(p, params) for p in partes if p.get("name") == "statement"), "")
            guia = next((texto_parte(p, params) for p in partes if p.get("name") == "guidance"), "")
            if not enunciado:
                continue
            codigo = cid.upper().replace("-", "-")
            funcion = funcion_de_control(cid)
            cuerpo = [
                f"# {codigo} {control['title']}",
                "",
                f"- Control: {codigo}",
                f"- Familia: {fam_id.upper()} — {NOMBRE_FAMILIA.get(fam_id, familia.get('title', ''))}",
                f"- Función CSF 2.0: {funcion} ({nombre_funcion(funcion)})",
                f"- Fuente: NIST SP 800-53 {version}",
                "",
                "## Control",
                "",
                enunciado or "(sin enunciado)",
            ]
            if guia:
                cuerpo += ["", "## Guía complementaria", "", guia]
            (salida / f"{cid}.md").write_text("\n".join(cuerpo) + "\n", encoding="utf-8")
            indice.append({"control": codigo, "familia": fam_id.upper(), "titulo": control["title"], "funcion": funcion})
            total += 1
    (salida.parent / "indice_controles.json").write_text(
        json.dumps({"fuente": f"NIST SP 800-53 {version}", "licencia": "Dominio público (CC0 1.0)",
                    "total": total, "controles": indice}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Controles base exportados: {total} (versión {version})")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
