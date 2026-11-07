"""Arma el informe técnico final: inserta los resultados de la evaluación y las figuras.

Lee docs/informe_tecnico.md y evaluacion/resultados/*.json, sustituye los marcadores [[...]] por tablas y
un análisis, embebe las figuras y produce docs/informe_tecnico.html (autocontenido, listo para
"Imprimir -> Guardar como PDF").

Uso: python scripts/armar_informe.py
"""
from __future__ import annotations

import base64
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DOCS = RAIZ / "docs"
RES = RAIZ / "evaluacion" / "resultados"


def _json(nombre: str) -> dict | None:
    ruta = RES / nombre
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else None


def tabla(encabezados: list[str], filas: list[list]) -> str:
    out = ["| " + " | ".join(encabezados) + " |", "|" + "|".join(["---"] * len(encabezados)) + "|"]
    for f in filas:
        out.append("| " + " | ".join("" if c is None else str(c) for c in f) + " |")
    return "\n".join(out)


def tabla_embeddings(d) -> str:
    if not d or not d.get("resultados"):
        return "_Pendiente de ejecutar la evaluación._"
    filas = [[r["modelo"], r["acierto@1"], r["acierto@3"], r["acierto@5"], r.get("latencia_consulta_ms"),
              (r["recursos"].get("tamano_disco_gb") or "n/d")] for r in d["resultados"]]
    t = tabla(["Modelo", "acierto@1", "acierto@3", "acierto@5", "latencia consulta (ms)", "disco (GB)"], filas)
    return t + f"\n\n*Modelo de embeddings elegido: **{d.get('recomendado')}**.*"


def tabla_modelos(d) -> str:
    if not d or not d.get("resultados"):
        return "_Pendiente de ejecutar la evaluación._"
    filas = [[r["modelo"], r["recursos"].get("parametros"), r.get("fidelidad_media"),
              r["latencia_media_ms"], r["esquema_valido_pct"], r["recursos"].get("memoria_gb")]
             for r in d["resultados"]]
    t = tabla(["Modelo", "parámetros", "fidelidad (0-5)", "latencia media (ms)", "esquema válido", "memoria (GB)"],
              filas)
    return t + f"\n\n*Ruta simple: **{d.get('ruta_simple')}**; ruta compleja: **{d.get('ruta_compleja')}**.*"


def tabla_sistema(d) -> str:
    if not d:
        return "_Pendiente de ejecutar la evaluación._"
    rag, g, ca, ag = d.get("rag", {}), d.get("guardrails", {}), d.get("cache", {}), d.get("agente", {})
    des = d.get("desempeno", {}).get("consultas", {}).get("latencia_ms", {})
    filas = [
        ["RAG: acierto@3 (familia)", rag.get("acierto@3")],
        ["RAG: fidelidad con contexto (0-5)", rag.get("fidelidad_con_rag")],
        ["RAG: fidelidad sin contexto (0-5)", rag.get("fidelidad_sin_rag")],
        ["Guardrails: bloqueos correctos", g.get("bloqueos_correctos_pct")],
        ["Guardrails: falsos positivos", g.get("falsos_positivos_pct")],
        ["Enrutador: aciertos", d.get("enrutador", {}).get("aciertos_pct")],
        ["Caché: aciertos exactos", f"{ca.get('aciertos_exactos')}/{ca.get('consultas')}"],
        ["Caché: reducción de latencia", ca.get("reduccion_latencia_pct")],
        ["Agente: iteraciones promedio", ag.get("iteraciones_promedio")],
        ["Desempeño: latencia media/p95 (ms)", f"{des.get('promedio')} / {des.get('p95')}"],
    ]
    return tabla(["Métrica", "Valor"], filas)


def analisis(d) -> str:
    if not d:
        return "_Pendiente de ejecutar la evaluación._"
    rag = d.get("rag", {})
    partes = []
    if rag.get("fidelidad_con_rag") and rag.get("fidelidad_sin_rag"):
        delta = rag["fidelidad_con_rag"] - rag["fidelidad_sin_rag"]
        partes.append(f"El RAG aumenta la fidelidad al contexto en {delta:.1f} puntos frente a la generación "
                      f"sin recuperación, lo que confirma su aporte.")
    g = d.get("guardrails", {})
    if g:
        partes.append(f"Los guardrails bloquean el {g.get('bloqueos_correctos_pct', 0)*100:.0f}% de las "
                      f"entradas problemáticas con {g.get('falsos_positivos_pct', 0)*100:.0f}% de falsos "
                      f"positivos sobre las normales.")
    ag = d.get("agente", {})
    if ag:
        partes.append(f"El ciclo de agente se activó en las consultas vagas con un promedio de "
                      f"{ag.get('iteraciones_promedio')} iteraciones.")
    return " ".join(partes) or "Ver el detalle en evaluacion/resultados/sistema.json."


def embeber_figuras(md: str) -> str:
    def repl(m):
        alt, rel = m.group(1), m.group(2)
        ruta = (DOCS / rel).resolve()
        if not ruta.exists():
            return f"*(figura pendiente: {rel})*"
        b64 = base64.b64encode(ruta.read_bytes()).decode()
        return f'<img alt="{alt}" src="data:image/png;base64,{b64}">'
    return re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", repl, md)


def md_a_html(md: str) -> str:
    try:
        import markdown
        cuerpo = markdown.markdown(md, extensions=["tables", "fenced_code"])
    except ImportError:
        cuerpo = _md_minimo(md)
    estilo = """
    body{font-family:Georgia,'Times New Roman',serif;max-width:850px;margin:0 auto;padding:40px;color:#1a1a1a;line-height:1.5}
    h1{font-size:1.8rem;border-bottom:2px solid #2d7dd2;padding-bottom:8px}
    h2{font-size:1.3rem;margin-top:1.8em;color:#13395e;border-bottom:1px solid #ccc;padding-bottom:4px}
    h3{font-size:1.05rem;color:#13395e}
    table{border-collapse:collapse;width:100%;margin:1em 0;font-size:.85rem}
    th,td{border:1px solid #bbb;padding:6px 9px;text-align:left}
    th{background:#eef3f8}
    img{max-width:100%;display:block;margin:12px auto;border:1px solid #ddd}
    code{background:#f2f2f2;padding:1px 4px;border-radius:3px;font-size:.85em}
    blockquote{color:#555;border-left:3px solid #2d7dd2;margin:1em 0;padding-left:12px}
    @media print{h2{page-break-after:avoid}table,img{page-break-inside:avoid}}
    """
    return f"<!DOCTYPE html><html lang='es'><head><meta charset='utf-8'><style>{estilo}</style></head><body>{cuerpo}</body></html>"


def _md_minimo(md: str) -> str:
    # respaldo si no está instalado 'markdown': solo para no fallar
    html = md
    for n in (3, 2, 1):
        html = re.sub(rf"^{'#'*n}\s+(.+)$", rf"<h{n}>\1</h{n}>", html, flags=re.M)
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
    return html.replace("\n\n", "<p>")


def main() -> None:
    md = (DOCS / "informe_tecnico.md").read_text(encoding="utf-8")
    md = re.sub(r"^---.*?---\s*", "", md, count=1, flags=re.S)  # quitar frontmatter
    md = md.replace("[[TABLA_EMBEDDINGS]]", tabla_embeddings(_json("embeddings.json")))
    md = md.replace("[[TABLA_MODELOS]]", tabla_modelos(_json("modelos.json")))
    sistema = _json("sistema.json")
    md = md.replace("[[TABLA_SISTEMA]]", tabla_sistema(sistema))
    md = md.replace("[[ANALISIS]]", analisis(sistema))
    md = md.replace("> `", "").replace("`\n", "\n")  # limpiar envoltura de los marcadores
    (DOCS / "informe_tecnico_final.md").write_text(md, encoding="utf-8")
    html = md_a_html(embeber_figuras(md))
    (DOCS / "informe_tecnico.html").write_text(html, encoding="utf-8")
    print("Informe armado: docs/informe_tecnico.html (abrir e Imprimir -> Guardar como PDF)")
    print("También: docs/informe_tecnico_final.md")


if __name__ == "__main__":
    main()
