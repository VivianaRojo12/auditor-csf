"""Genera las figuras del informe a partir de evaluacion/resultados/*.json.

Uso: python -m evaluacion.graficas  (se ejecuta al final de ejecutar_todo)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RAIZ = Path(__file__).resolve().parent.parent
RES = RAIZ / "evaluacion" / "resultados"
FIG = RAIZ / "docs" / "figuras"

# paleta sobria, legible en impresión
AZUL, VERDE, AMBAR, ROJO, GRIS = "#2d7dd2", "#3fb950", "#f5a623", "#e5484d", "#9fb0c0"
plt.rcParams.update({"figure.dpi": 130, "font.size": 10, "axes.titlesize": 12})


def _cargar(nombre):
    ruta = RES / nombre
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else None


def fig_embeddings(d):
    r = d["resultados"]
    if not r:
        return
    nombres = [x["modelo"] for x in r]
    fig, ax = plt.subplots(figsize=(7, 3.6))
    x = range(len(nombres))
    ax.bar([i - 0.2 for i in x], [v["acierto@1"] for v in r], 0.2, label="acierto@1", color=AZUL)
    ax.bar([i for i in x], [v["acierto@3"] for v in r], 0.2, label="acierto@3", color=VERDE)
    ax.bar([i + 0.2 for i in x], [v["acierto@5"] for v in r], 0.2, label="acierto@5", color=AMBAR)
    ax.set_xticks(list(x)); ax.set_xticklabels(nombres, rotation=10)
    ax.set_ylim(0, 1); ax.set_ylabel("acierto@k"); ax.set_title("Recuperación por modelo de embeddings")
    ax.legend(); fig.tight_layout(); fig.savefig(FIG / "embeddings_acierto.png"); plt.close(fig)


def fig_modelos(d):
    r = [x for x in d["resultados"] if x.get("fidelidad_media") is not None]
    if not r:
        return
    fig, ax1 = plt.subplots(figsize=(7, 3.6))
    nombres = [x["modelo"] for x in r]
    x = range(len(nombres))
    ax1.bar(x, [v["latencia_media_ms"] / 1000 for v in r], 0.5, color=AZUL, label="latencia media (s)")
    ax1.set_ylabel("latencia media (s)", color=AZUL)
    ax1.set_xticks(list(x)); ax1.set_xticklabels(nombres, rotation=10)
    ax2 = ax1.twinx()
    ax2.plot(list(x), [v["fidelidad_media"] for v in r], "o-", color=ROJO, label="fidelidad (0-5)")
    ax2.set_ylim(0, 5); ax2.set_ylabel("fidelidad (0-5)", color=ROJO)
    ax1.set_title("Modelos de lenguaje: latencia vs. fidelidad")
    fig.tight_layout(); fig.savefig(FIG / "modelos_latencia_fidelidad.png"); plt.close(fig)


def fig_sistema(d):
    rag = d.get("rag", {})
    if rag:
        fig, ax = plt.subplots(figsize=(6, 3.4))
        etiquetas = ["Sin RAG", "Con RAG"]
        valores = [rag.get("fidelidad_sin_rag") or 0, rag.get("fidelidad_con_rag") or 0]
        ax.bar(etiquetas, valores, color=[GRIS, VERDE]); ax.set_ylim(0, 5)
        ax.set_ylabel("fidelidad al contexto (0-5)"); ax.set_title("Impacto del RAG en la fidelidad")
        for i, v in enumerate(valores):
            ax.text(i, v + 0.1, f"{v:.1f}", ha="center")
        fig.tight_layout(); fig.savefig(FIG / "rag_impacto.png"); plt.close(fig)

    desemp = d.get("desempeno", {}).get("latencia_por_capa_ms", {})
    if desemp:
        items = sorted(desemp.items(), key=lambda kv: kv[1]["promedio"], reverse=True)[:8]
        fig, ax = plt.subplots(figsize=(7, 3.8))
        ax.barh([k for k, _ in items][::-1], [v["promedio"] for _, v in items][::-1], color=AZUL)
        ax.set_xlabel("latencia promedio (ms)"); ax.set_title("Latencia promedio por capa / etapa")
        fig.tight_layout(); fig.savefig(FIG / "latencia_por_capa.png"); plt.close(fig)


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    for nombre, fn in [("embeddings.json", fig_embeddings), ("modelos.json", fig_modelos),
                       ("sistema.json", fig_sistema)]:
        d = _cargar(nombre)
        if d:
            fn(d)
            print(f"[gráficas] {nombre} procesado")
    print(f"[gráficas] figuras en {FIG}")


if __name__ == "__main__":
    main()
