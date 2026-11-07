"""Experimento de selección del modelo de embeddings (R3).

Para cada modelo candidato: indexa el corpus de controles en una base en memoria, ejecuta los casos de
prueba de recuperación y mide acierto@k (a nivel familia de control), latencia media de embebido y
recursos reportados por Ollama. El resultado alimenta la decisión de arquitectura del embedding.

Uso: python -m evaluacion.experimento_embeddings [modelo1 modelo2 ...]
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from evaluacion._comun import acierto_en_k, cargar, guardar, servidor_de  # noqa: E402
from servicio.config import obtener  # noqa: E402
from servicio.contexto.rag import ConstructorContexto  # noqa: E402
from servicio.datos.ollama import AdaptadorOllama  # noqa: E402
from servicio.datos.vectorial import VectorialMemoria  # noqa: E402

CANDIDATOS = ["nomic-embed-text", "bge-m3", "mxbai-embed-large"]
RAIZ = Path(__file__).resolve().parent.parent


def evaluar_modelo(modelo: str, casos: list[dict], conf) -> dict:
    servidor = servidor_de(conf)
    base = VectorialMemoria()
    conf_local = conf.model_copy(deep=True)
    conf_local.embeddings.modelo = modelo
    contexto = ConstructorContexto(conf_local, servidor, base)

    t0 = time.perf_counter()
    ingesta = contexto.ingestar_corpus(RAIZ / "corpus" / "controles")
    t_ingesta = time.perf_counter() - t0

    aciertos = {1: 0, 3: 0, 5: 0}
    exactos = 0
    latencias = []
    detalle = []
    for caso in casos:
        rec, _ = _recuperar(contexto, caso["texto"], latencias)
        controles = [f.control for f in rec]
        fila = {"id": caso["id"], "recuperados": controles[:5]}
        for k in aciertos:
            if acierto_en_k(controles, caso["familia"], k):
                aciertos[k] += 1
                fila[f"acierto@{k}"] = True
        if set(caso.get("controles_esperados", [])) & set(controles[:5]):
            exactos += 1
        detalle.append(fila)

    n = len(casos)
    detalles_modelo = servidor.detalles_modelo(modelo)
    return {
        "modelo": modelo,
        "acierto@1": round(aciertos[1] / n, 3),
        "acierto@3": round(aciertos[3] / n, 3),
        "acierto@5": round(aciertos[5] / n, 3),
        "acierto_exacto@5": round(exactos / n, 3),
        "latencia_consulta_ms": round(sum(latencias) / len(latencias), 1) if latencias else None,
        "tiempo_ingesta_s": round(t_ingesta, 1),
        "fragmentos": ingesta["fragmentos"],
        "recursos": {"memoria_gb": detalles_modelo.get("memoria_gb"),
                     "tamano_disco_gb": detalles_modelo.get("tamano_disco_gb")},
        "detalle": detalle,
    }


def _recuperar(contexto, texto, latencias):
    import time as _t
    inicio = _t.perf_counter()
    rec = contexto.recuperar(texto)
    latencias.append((_t.perf_counter() - inicio) * 1000)
    return rec.fragmentos, None


def main(modelos: list[str] | None = None) -> dict:
    conf = obtener()
    casos = cargar("casos_rag.json")["casos"]
    candidatos = modelos or CANDIDATOS
    resultados = []
    for m in candidatos:
        print(f"[embeddings] evaluando {m} sobre {len(casos)} casos...")
        try:
            resultados.append(evaluar_modelo(m, casos, conf))
        except Exception as e:  # un modelo no instalado no debe tumbar el experimento
            print(f"  omitido ({type(e).__name__}: {e})")
    resultados.sort(key=lambda r: (r["acierto@3"], -(r["latencia_consulta_ms"] or 1e9)), reverse=True)
    salida = {"candidatos": candidatos, "n_casos": len(casos), "resultados": resultados,
              "recomendado": resultados[0]["modelo"] if resultados else None}
    ruta = guardar("embeddings.json", salida)
    print(f"[embeddings] recomendado: {salida['recomendado']} -> {ruta}")
    return salida


if __name__ == "__main__":
    main(sys.argv[1:] or None)
