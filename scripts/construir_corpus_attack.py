"""Genera el corpus ATT&CK (Linux y contenedores) en Markdown a partir del paquete STIX oficial.

Uso: python scripts/construir_corpus_attack.py RUTA/enterprise-attack.json corpus/attack
Fuente: https://github.com/mitre-attack/attack-stix-data (licencia en corpus/LICENCIAS.md)
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

PLATAFORMAS = {"Linux", "Containers"}


def limpiar(texto: str) -> str:
    texto = re.sub(r"\(Citation:[^)]*\)", "", texto or "")
    texto = re.sub(r"<code>(.*?)</code>", r"`\1`", texto)
    texto = re.sub(r"\[([^\]]+)\]\(https://attack\.mitre\.org[^)]*\)", r"\1", texto)
    texto = re.sub(r"<[^>]+>", "", texto)
    texto = re.sub(r"[ \t]+", " ", texto)
    return re.sub(r"\n{3,}", "\n\n", texto).strip()


def id_externo(obj):
    for ref in obj.get("external_references", []):
        if ref.get("source_name") == "mitre-attack":
            return ref.get("external_id"), ref.get("url")
    return None, None


def main(origen: str, destino: str):
    datos = json.loads(Path(origen).read_text(encoding="utf-8"))
    objetos = datos["objects"]
    por_id = {o["id"]: o for o in objetos}
    version = next((o.get("x_mitre_version") for o in objetos if o["type"] == "x-mitre-collection"), "")
    mitigaciones = defaultdict(list)
    for o in objetos:
        if o["type"] == "relationship" and o.get("relationship_type") == "mitigates" and not o.get("revoked"):
            fuente = por_id.get(o["source_ref"])
            if fuente and fuente["type"] == "course-of-action" and not fuente.get("x_mitre_deprecated"):
                mitigaciones[o["target_ref"]].append((fuente, limpiar(o.get("description", ""))))
    padres = {}
    for o in objetos:
        if o["type"] == "attack-pattern":
            tid, _ = id_externo(o)
            if tid:
                padres[tid] = o.get("name")
    salida = Path(destino)
    salida.mkdir(parents=True, exist_ok=True)
    total = 0
    catalogo_mitig = {}
    for o in objetos:
        if o["type"] != "attack-pattern" or o.get("revoked") or o.get("x_mitre_deprecated"):
            continue
        if not PLATAFORMAS & set(o.get("x_mitre_platforms", [])):
            continue
        tid, url = id_externo(o)
        if not tid:
            continue
        nombre = o["name"]
        if "." in tid:
            nombre = f"{padres.get(tid.split('.')[0], '')}: {nombre}"
        tacticas = [f["phase_name"] for f in o.get("kill_chain_phases", []) if f.get("kill_chain_name") == "mitre-attack"]
        partes = [
            f"# {tid} {nombre}",
            "",
            f"- Identificador: {tid}",
            f"- Tácticas: {', '.join(tacticas)}",
            f"- Plataformas: {', '.join(o.get('x_mitre_platforms', []))}",
            f"- URL: {url}",
            "",
            "## Descripción",
            "",
            limpiar(o.get("description", "")),
        ]
        deteccion = limpiar(o.get("x_mitre_detection", ""))
        if deteccion:
            partes += ["", "## Detección", "", deteccion]
        lista = mitigaciones.get(o["id"], [])
        if lista:
            partes += ["", "## Mitigaciones", ""]
            for m, desc in lista:
                mid, _ = id_externo(m)
                catalogo_mitig[mid] = {"id": mid, "nombre": m["name"], "descripcion": limpiar(m.get("description", ""))}
                partes.append(f"- {mid} {m['name']}: {desc[:400]}")
        (salida / f"{tid}.md").write_text("\n".join(partes) + "\n", encoding="utf-8")
        total += 1
    (salida.parent / "mitigaciones_attack.json").write_text(
        json.dumps({"fuente": "MITRE ATT&CK Enterprise", "version": version,
                    "mitigaciones": sorted(catalogo_mitig.values(), key=lambda x: x["id"])},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Técnicas exportadas: {total}; mitigaciones: {len(catalogo_mitig)}; versión ATT&CK {version}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
