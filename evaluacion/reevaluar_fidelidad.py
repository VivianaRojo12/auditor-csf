"""Reevaluación de la fidelidad con y sin RAG, con un procedimiento corregido.

Corrige tres problemas de la medición original (evaluar_sistema.eval_rag):
  1. Ambas respuestas (con y sin RAG) se califican contra los MISMOS controles de referencia recuperados,
     en lugar de comparar la respuesta sin RAG contra un contexto vacío.
  2. El juez recibe el contexto y la respuesta completos (antes se recortaban a 2,500 y 1,500 caracteres).
  3. El juez es qwen2.5:7b, con espacio suficiente para responder (antes era el modelo de la ruta compleja
     con 120 tokens, lo que podía cortar el JSON y descartar la calificación).

Además calcula una métrica determinista que no depende del juez: el porcentaje de hallazgos cuyo control
citado está entre los controles recuperados (citas válidas).

Guarda el detalle caso por caso en evaluacion/resultados/fidelidad.json (se actualiza después de cada caso,
así que si se interrumpe con Ctrl+C se conserva lo avanzado), actualiza la sección "rag" de sistema.json y
regenera las figuras.

Uso: .\\.venv\\Scripts\\python.exe -m evaluacion.reevaluar_fidelidad [--casos 22] [--juez qwen2.5:7b]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from evaluacion._comun import RESULTADOS, cargar, guardar  # noqa: E402
from evaluacion.evaluar_sistema import _generar, asegurar_corpus  # noqa: E402
from servicio.contenedor import Contenedor  # noqa: E402
from servicio.dominio import Seccion  # noqa: E402

ESQUEMA = {
    "type": "object",
    "properties": {"puntaje": {"type": "integer"}, "justificacion": {"type": "string"}},
    "required": ["puntaje", "justificacion"],
}


def prompt_juez(controles: str, respuesta: str) -> str:
    return (
        "Verifica los hallazgos de una auditoría contra los controles de referencia.\n\n"
        f"CONTROLES DE REFERENCIA:\n{controles[:9000]}\n\n"
        f"RESPUESTA A EVALUAR (JSON con hallazgos):\n{respuesta[:5000]}\n\n"
        "Califica de 0 a 5 qué proporción de los hallazgos está sustentada en los controles de referencia: "
        "el control citado aparece en las referencias y lo que se afirma de él coincide con su texto. "
        "5 = todos los hallazgos están sustentados; 0 = ninguno lo está o la respuesta no contiene hallazgos. "
        "Responde solo con el JSON, con una justificación de una frase."
    )


def juez(c: Contenedor, modelo: str, controles: str, respuesta: str) -> int:
    try:
        r = c.servidor.generar(
            modelo,
            [{"role": "system", "content": "Eres un evaluador estricto. Responde solo en JSON."},
             {"role": "user", "content": prompt_juez(controles, respuesta)}],
            ESQUEMA, 250, {"temperature": 0, "num_ctx": 8192})
        texto = r.texto
        try:
            p = int(json.loads(texto).get("puntaje", -1))
        except Exception:
            m = re.search(r'"puntaje"\s*:\s*(\d)', texto)
            p = int(m.group(1)) if m else -1
        return max(-1, min(5, p))
    except Exception as e:  # noqa: BLE001
        print(f"    (juez sin respuesta: {e})")
        return -1


def _norm(control: str) -> str:
    return re.sub(r"\s+", "", str(control).upper()).split("(")[0]


def hallazgos(respuesta: str) -> list[dict]:
    try:
        h = json.loads(respuesta).get("hallazgos", [])
        return h if isinstance(h, list) else []
    except Exception:
        return []


def citas_validas(respuesta: str, recuperados: set[str]) -> tuple[int, int]:
    hs = hallazgos(respuesta)
    validas = sum(1 for h in hs if _norm(h.get("control_id", "")) in recuperados)
    return validas, len(hs)


def resumen(detalle: list[dict], juez_modelo: str) -> dict:
    def prom(clave):
        v = [d[clave] for d in detalle if d[clave] >= 0]
        return round(sum(v) / len(v), 2) if v else None

    def pct(clave_v, clave_t):
        v = sum(d[clave_v] for d in detalle)
        t = sum(d[clave_t] for d in detalle)
        return round(v / t, 3) if t else None

    return {
        "n_casos": len(detalle),
        "juez": juez_modelo,
        "fidelidad_con_rag": prom("fid_con"),
        "fidelidad_sin_rag": prom("fid_sin"),
        "calificaciones_validas_con": sum(1 for d in detalle if d["fid_con"] >= 0),
        "calificaciones_validas_sin": sum(1 for d in detalle if d["fid_sin"] >= 0),
        "citas_validas_con_rag": pct("citas_ok_con", "hallazgos_con"),
        "citas_validas_sin_rag": pct("citas_ok_sin", "hallazgos_sin"),
        "hallazgos_promedio_con": round(sum(d["hallazgos_con"] for d in detalle) / len(detalle), 2) if detalle else None,
        "hallazgos_promedio_sin": round(sum(d["hallazgos_sin"] for d in detalle) / len(detalle), 2) if detalle else None,
        "metodo": "ambas respuestas calificadas contra los mismos controles recuperados; contexto completo",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--casos", type=int, default=22)
    ap.add_argument("--juez", default="qwen2.5:7b")
    args = ap.parse_args()

    c = Contenedor()
    asegurar_corpus(c)
    casos = cargar("casos_rag.json")["casos"][: args.casos]
    print(f"[fidelidad] {len(casos)} casos, juez {args.juez}")
    detalle: list[dict] = []
    inicio = time.time()
    try:
        for i, caso in enumerate(casos, 1):
            t0 = time.time()
            rec = c.contexto.recuperar(caso["texto"])
            fuentes, _ = c.contexto.armar_fuentes(rec.fragmentos)
            recuperados = {_norm(f.control) for f in rec.fragmentos}
            seccion = Seccion(1, caso["id"], caso["texto"])
            con = _generar(c, seccion, fuentes)
            sin = _generar(c, seccion, "(sin controles de referencia)")
            ok_con, n_con = citas_validas(con, recuperados)
            ok_sin, n_sin = citas_validas(sin, recuperados)
            d = {"id": caso["id"],
                 "fid_con": juez(c, args.juez, fuentes, con),
                 "fid_sin": juez(c, args.juez, fuentes, sin),
                 "hallazgos_con": n_con, "citas_ok_con": ok_con,
                 "hallazgos_sin": n_sin, "citas_ok_sin": ok_sin}
            detalle.append(d)
            guardar("fidelidad.json", {"resumen": resumen(detalle, args.juez), "detalle": detalle})
            transcurrido = time.time() - inicio
            restante = transcurrido / i * (len(casos) - i)
            print(f"  {i}/{len(casos)} {caso['id']}: con RAG {d['fid_con']}, sin RAG {d['fid_sin']} "
                  f"({time.time() - t0:.0f} s; faltan ~{restante / 60:.0f} min)")
    except KeyboardInterrupt:
        print("\n[fidelidad] interrumpido; se conservan los casos terminados.")

    if not detalle:
        return
    res = resumen(detalle, args.juez)
    ruta_sistema = RESULTADOS / "sistema.json"
    if ruta_sistema.exists():
        sistema = json.loads(ruta_sistema.read_text(encoding="utf-8"))
        sistema.setdefault("rag", {})["fidelidad_original"] = {
            "con_rag": sistema["rag"].get("fidelidad_con_rag"), "sin_rag": sistema["rag"].get("fidelidad_sin_rag")}
        sistema["rag"].update({k: v for k, v in res.items() if k != "n_casos"})
        sistema["rag"]["n_casos_fidelidad"] = res["n_casos"]
        guardar("sistema.json", sistema)
    try:
        from evaluacion import graficas
        graficas.main()
    except Exception as e:  # noqa: BLE001
        print(f"[fidelidad] no se regeneraron las figuras: {e}")
    print("[fidelidad] RESULTADO:")
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
