"""Orquesta toda la evaluación y calibra la configuración.

1) Experimento de embeddings -> elige el modelo de embeddings.
2) Experimento de modelos de lenguaje -> elige los modelos de las rutas simple y compleja.
3) Escribe esas elecciones en config.yaml (calibración).
4) Reindexa el corpus con el embedding elegido y evalúa el sistema completo.
5) Genera las gráficas del informe.

Uso: python -m evaluacion.ejecutar_todo
Requiere Ollama en ejecución con los modelos descargados.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from evaluacion import evaluar_sistema, experimento_embeddings, experimento_modelos  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
CONFIG = RAIZ / "config.yaml"


def calibrar_config(embedding: str | None, simple: str | None, compleja: str | None) -> None:
    datos = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    if embedding:
        datos["embeddings"]["modelo"] = embedding
    if simple:
        datos["modelos"]["rutas"]["simple"]["modelo"] = simple
    if compleja:
        datos["modelos"]["rutas"]["compleja"]["modelo"] = compleja
    CONFIG.write_text(yaml.safe_dump(datos, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"[calibración] embedding={embedding} simple={simple} compleja={compleja} escritos en config.yaml")


def main() -> None:
    print("=== 1/5 Experimento de embeddings ===")
    emb = experimento_embeddings.main()
    print("=== 2/5 Experimento de modelos de lenguaje ===")
    mod = experimento_modelos.main()

    print("=== 3/5 Calibración de config.yaml ===")
    calibrar_config(emb.get("recomendado"), mod.get("ruta_simple"), mod.get("ruta_compleja"))

    print("=== 4/5 Reindexado del corpus con el embedding elegido ===")
    from servicio.config import obtener
    obtener.cache_clear()  # recargar config calibrada
    conf = obtener()
    shutil.rmtree(conf.dir_datos / "chroma", ignore_errors=True)
    import scripts.ingestar_corpus as ing
    ing.main()

    print("=== 5/5 Evaluación del sistema completo ===")
    evaluar_sistema.main()

    print("=== Gráficas ===")
    from evaluacion import graficas
    graficas.main()

    print("=== Armado del informe técnico ===")
    import scripts.armar_informe as ai
    ai.main()
    print("\nEvaluación terminada. Resultados en evaluacion/resultados/, figuras en docs/figuras/ "
          "e informe en docs/informe_tecnico.html.")


if __name__ == "__main__":
    main()
