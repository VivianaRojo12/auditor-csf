"""Evaluación del sistema completo (R9): RAG, guardrails, caché, enrutador, ciclo de agente y desempeño.

Levanta el contenedor con la configuración vigente (Ollama + Chroma), se asegura de que el corpus esté
indexado y ejecuta los conjuntos de prueba. Escribe evaluacion/resultados/sistema.json.

Uso: python -m evaluacion.evaluar_sistema
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from evaluacion._comun import acierto_en_k, cargar, guardar  # noqa: E402
from servicio.contenedor import Contenedor  # noqa: E402
from servicio.contexto import prompts  # noqa: E402
from servicio.dominio import Seccion  # noqa: E402
from servicio.guardrails import verificaciones  # noqa: E402
from servicio.observabilidad.trazas import observador  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent


def asegurar_corpus(c: Contenedor) -> None:
    if c.base.contar() == 0:
        import hashlib
        r = c.contexto.ingestar_corpus(RAIZ / "corpus" / "controles")
        archivos = sorted((RAIZ / "corpus" / "controles").glob("*.md"))
        firma = hashlib.sha256("".join(f"{a.name}{a.stat().st_size}" for a in archivos).encode()).hexdigest()
        c.docs.guardar_documento("corpus-controles", "NIST SP 800-53 Rev. 5", "md", firma, r["fragmentos"], b"")


def eval_rag(c: Contenedor) -> dict:
    casos = cargar("casos_rag.json")["casos"]
    ac = {1: 0, 3: 0, 5: 0}
    fid_con, fid_sin = [], []
    for caso in casos:
        rec = c.contexto.recuperar(caso["texto"])
        controles = [f.control for f in rec.fragmentos]
        for k in ac:
            if acierto_en_k(controles, caso["familia"], k):
                ac[k] += 1
        fuentes, _ = c.contexto.armar_fuentes(rec.fragmentos)
        seccion = Seccion(1, caso["id"], caso["texto"])
        con = _generar(c, seccion, fuentes)
        sin = _generar(c, seccion, "(sin controles de referencia)")
        fid_con.append(_juez(c, caso["texto"], con, fuentes))
        fid_sin.append(_juez(c, caso["texto"], sin, "(sin contexto)"))
    n = len(casos)
    fc = [x for x in fid_con if x >= 0]
    fs = [x for x in fid_sin if x >= 0]
    return {"n_casos": n, "acierto@1": round(ac[1] / n, 3), "acierto@3": round(ac[3] / n, 3),
            "acierto@5": round(ac[5] / n, 3),
            "fidelidad_con_rag": round(sum(fc) / len(fc), 2) if fc else None,
            "fidelidad_sin_rag": round(sum(fs) / len(fs), 2) if fs else None}


def _generar(c, seccion, fuentes):
    try:
        r = c.gateway.generar([{"role": "system", "content": prompts.SISTEMA_AUDITOR},
                               {"role": "user", "content": prompts.prompt_analisis(seccion, fuentes)}],
                              ruta="simple", esquema=prompts.ESQUEMA_ANALISIS, usar_respaldo=True)
        return r.texto
    except Exception:
        return "{}"


def _juez(c, pregunta, respuesta, contexto):
    try:
        r = c.gateway.generar([{"role": "system", "content": "Evaluador estricto. Responde en JSON."},
                               {"role": "user", "content": prompts.prompt_juez(pregunta, respuesta, contexto)}],
                              ruta="compleja", esquema=prompts.ESQUEMA_JUEZ, max_tokens=120, usar_respaldo=True)
        return int(json.loads(r.texto).get("puntaje", 0))
    except Exception:
        return -1


def eval_guardrails(c: Contenedor) -> dict:
    datos = cargar("guardrails.json")
    tp = fp = fn = tn = 0
    detalle = []
    for item in datos["problematicas"]:
        res = verificaciones.verificar_entrada(item["texto"], c.conf.guardrails)
        if item["esperado"] == "bloquear":
            ok = not res.aprobada
            tp += int(ok); fn += int(not ok)
        else:  # anonimizar: debe aprobar pero haber saneado
            saneado = res.texto_saneado != item["texto"]
            ok = res.aprobada and saneado
            tp += int(ok); fn += int(not ok)
        detalle.append({"id": item["id"], "tipo": item["tipo"], "correcto": ok})
    for item in datos["normales"]:
        res = verificaciones.verificar_entrada(item["texto"], c.conf.guardrails)
        ok = res.aprobada
        tn += int(ok); fp += int(not ok)
        detalle.append({"id": item["id"], "tipo": "normal", "correcto": ok})
    prob = len(datos["problematicas"])
    norm = len(datos["normales"])
    return {"problematicas": prob, "normales": norm,
            "bloqueos_correctos_pct": round(tp / prob, 3),
            "falsos_positivos_pct": round(fp / norm, 3),
            "verdaderos_negativos": tn, "detalle": detalle}


def eval_cache(c: Contenedor) -> dict:
    version = c.version_corpus()
    textos = [caso["texto"] for caso in cargar("casos_rag.json")["casos"][:6]]
    parafrasis = {t: "En la organización, " + t.lower() for t in textos}
    c.cache_almacen.vaciar()
    lat_fria, lat_caliente = [], []
    aciertos = 0
    for t in textos:  # primera pasada (fría)
        s = Seccion(1, "s", t)
        _, ms = _cron(c, s, version)
        lat_fria.append(ms)
    for t in textos:  # segunda pasada idéntica (debe pegar exacta)
        s = Seccion(1, "s", t)
        r, ms = _cron(c, s, version)
        lat_caliente.append(ms)
        aciertos += int(r.cache in {"exacta", "semantica"})
    semanticos = 0
    for t, p in parafrasis.items():  # parafraseadas (pueden pegar semántica)
        s = Seccion(1, "s", p)
        r, _ = _cron(c, s, version)
        semanticos += int(r.cache == "semantica")
    media = lambda x: round(sum(x) / len(x), 1) if x else 0
    return {"consultas": len(textos), "aciertos_exactos": aciertos, "aciertos_semanticos_parafrasis": semanticos,
            "latencia_fria_ms": media(lat_fria), "latencia_caliente_ms": media(lat_caliente),
            "reduccion_latencia_pct": round(1 - media(lat_caliente) / media(lat_fria), 3) if media(lat_fria) else None}


def _cron(c, seccion, version):
    inicio = time.perf_counter()
    r = c.orquestador.analizar_seccion(seccion, version)
    return r, (time.perf_counter() - inicio) * 1000


def eval_enrutador(c: Contenedor) -> dict:
    casos = cargar("enrutador.json")["casos"]
    correctos = 0
    detalle = []
    for caso in casos:
        d = c.enrutador.clasificar(Seccion(1, caso["titulo"], caso["texto"]))
        ok = d.ruta == caso["ruta_esperada"]
        correctos += int(ok)
        detalle.append({"id": caso["id"], "esperada": caso["ruta_esperada"], "obtenida": d.ruta,
                        "puntaje": d.puntaje, "correcto": ok})
    return {"n": len(casos), "aciertos_pct": round(correctos / len(casos), 3), "detalle": detalle}


def eval_agente(c: Contenedor) -> dict:
    # consultas vagas/ruidosas que suelen dar recuperación pobre en el primer intento
    pruebas = ["procedimiento interno número 4 del anexo",
               "lo que marca el reglamento sobre el tema del punto anterior",
               "disposiciones generales aplicables",
               "cumplir con lo establecido por la normatividad vigente"]
    version = c.version_corpus()
    mejoras, iteraciones = 0, []
    for t in pruebas:
        observador.nueva_traza()
        r = c.orquestador.analizar_seccion(Seccion(1, "prueba", t), version)
        iteraciones.append(r.iteraciones_agente)
        mejoras += int(r.iteraciones_agente > 1 and len(r.hallazgos) > 0)
    return {"consultas": len(pruebas), "iteraciones_promedio": round(sum(iteraciones) / len(iteraciones), 2),
            "con_reformulacion": sum(1 for i in iteraciones if i > 1),
            "mejoraron_tras_reformular": mejoras}


def main() -> dict:
    c = Contenedor()
    print(f"[sistema] proveedor {c.conf.proveedor_modelos}, embeddings {c.conf.embeddings.modelo}")
    asegurar_corpus(c)
    salida = {"configuracion": {"modelos": c.conf.modelos.model_dump(), "embeddings": c.conf.embeddings.modelo,
                                "recuperacion": c.conf.recuperacion, "agente": c.conf.agente}}
    print("[sistema] guardrails..."); salida["guardrails"] = eval_guardrails(c)
    print("[sistema] enrutador..."); salida["enrutador"] = eval_enrutador(c)
    print("[sistema] RAG (con/sin, acierto@k, fidelidad)..."); salida["rag"] = eval_rag(c)
    print("[sistema] caché..."); salida["cache"] = eval_cache(c)
    print("[sistema] ciclo de agente..."); salida["agente"] = eval_agente(c)
    salida["desempeno"] = c.eventos.resumen_metricas()
    ruta = guardar("sistema.json", salida)
    print(f"[sistema] listo -> {ruta}")
    return salida


if __name__ == "__main__":
    main()
