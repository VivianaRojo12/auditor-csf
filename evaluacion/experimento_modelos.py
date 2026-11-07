"""Experimento de selección del modelo de lenguaje y del criterio del enrutador (R3, C6).

Para cada LLM candidato, analiza un conjunto fijo de secciones (con el mismo contexto recuperado) y mide:
latencia, tokens de salida, validez del esquema JSON y fidelidad al contexto según un modelo juez.
La conclusión sustenta qué modelo va a la ruta simple y cuál a la compleja.

Uso: python -m evaluacion.experimento_modelos [modelo1 modelo2 ...]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from evaluacion._comun import cargar, cronometrar, guardar, servidor_de  # noqa: E402
from servicio.config import obtener  # noqa: E402
from servicio.contexto import prompts  # noqa: E402
from servicio.contexto.rag import ConstructorContexto  # noqa: E402
from servicio.datos.ollama import AdaptadorOllama  # noqa: E402
from servicio.datos.vectorial import VectorialMemoria  # noqa: E402
from servicio.dominio import Seccion  # noqa: E402

CANDIDATOS = ["qwen2.5:3b", "llama3.2:3b", "qwen2.5:7b"]
RAIZ = Path(__file__).resolve().parent.parent


def preparar_contexto(conf):
    servidor = servidor_de(conf)
    base = VectorialMemoria()
    ctx = ConstructorContexto(conf, servidor, base)
    ctx.ingestar_corpus(RAIZ / "corpus" / "controles")
    return servidor, ctx


def juez(servidor, modelo_juez, pregunta, respuesta, contexto, conf) -> int:
    try:
        r = servidor.generar(modelo_juez,
                             [{"role": "system", "content": "Eres un evaluador estricto. Responde en JSON."},
                              {"role": "user", "content": prompts.prompt_juez(pregunta, respuesta, contexto)}],
                             prompts.ESQUEMA_JUEZ, 120, {"temperature": 0, "num_ctx": conf.modelos.num_ctx})
        return int(json.loads(r.texto).get("puntaje", 0))
    except Exception:
        return -1


def main(modelos: list[str] | None = None) -> dict:
    conf = obtener()
    casos = cargar("casos_rag.json")["casos"][:8]
    servidor, ctx = preparar_contexto(conf)
    candidatos = modelos or CANDIDATOS
    modelo_juez = next((m for m in ["qwen2.5:7b", "qwen2.5:3b"] if m in candidatos), candidatos[-1])

    # contexto recuperado una sola vez por caso (igual para todos los modelos)
    contextos = []
    for caso in casos:
        rec = ctx.recuperar(caso["texto"])
        fuentes, refs = ctx.armar_fuentes(rec.fragmentos)
        contextos.append((caso, fuentes, refs))

    resultados = []
    for modelo in candidatos:
        print(f"[modelos] evaluando {modelo} sobre {len(casos)} secciones...")
        filas, latencias, tokens, validos, puntajes = [], [], [], 0, []
        try:
            for caso, fuentes, refs in contextos:
                seccion = Seccion(1, caso["id"], caso["texto"])
                mensajes = [{"role": "system", "content": prompts.SISTEMA_AUDITOR},
                            {"role": "user", "content": prompts.prompt_analisis(seccion, fuentes)}]
                r, ms = cronometrar(servidor.generar, modelo, mensajes, prompts.ESQUEMA_ANALISIS,
                                    conf.modelos.rutas["compleja"].tiempo_limite_s,
                                    {"temperature": 0.1, "num_ctx": conf.modelos.num_ctx, "num_predict": 900})
                latencias.append(ms)
                tokens.append(r.tokens_salida)
                try:
                    datos = json.loads(r.texto)
                    valido = isinstance(datos.get("hallazgos"), list)
                except json.JSONDecodeError:
                    valido = False
                validos += int(valido)
                p = juez(servidor, modelo_juez, caso["texto"], r.texto, fuentes, conf)
                if p >= 0:
                    puntajes.append(p)
                filas.append({"id": caso["id"], "latencia_ms": round(ms, 1), "tokens": r.tokens_salida,
                              "esquema_valido": valido, "fidelidad": p})
        except Exception as e:
            print(f"  omitido ({type(e).__name__}: {e})")
            continue
        n = len(filas)
        d = servidor.detalles_modelo(modelo)
        resultados.append({
            "modelo": modelo,
            "latencia_media_ms": round(sum(latencias) / n, 1),
            "latencia_max_ms": round(max(latencias), 1),
            "tokens_salida_media": round(sum(tokens) / n, 1),
            "esquema_valido_pct": round(validos / n, 3),
            "fidelidad_media": round(sum(puntajes) / len(puntajes), 2) if puntajes else None,
            "recursos": {"parametros": d.get("parametros"), "cuantizacion": d.get("cuantizacion"),
                         "memoria_gb": d.get("memoria_gb"), "tamano_disco_gb": d.get("tamano_disco_gb"),
                         "ventana_contexto": d.get("ventana_contexto"), "licencia": d.get("licencia")},
            "detalle": filas,
        })

    salida = {"candidatos": candidatos, "modelo_juez": modelo_juez, "n_secciones": len(casos),
              "resultados": resultados}
    # ruta simple: suficiente calidad y menor latencia; ruta compleja: mejor fidelidad
    validos = [r for r in resultados if r["fidelidad_media"] is not None]
    if validos:
        salida["ruta_simple"] = min(validos, key=lambda r: r["latencia_media_ms"])["modelo"]
        salida["ruta_compleja"] = max(validos, key=lambda r: (r["fidelidad_media"], -r["latencia_media_ms"]))["modelo"]
    ruta = guardar("modelos.json", salida)
    print(f"[modelos] simple: {salida.get('ruta_simple')} | compleja: {salida.get('ruta_compleja')} -> {ruta}")
    return salida


if __name__ == "__main__":
    main(sys.argv[1:] or None)
