"""Indexa el corpus de controles en la base vectorial. Ejecutar una vez antes de levantar el servicio.

Uso: python -m scripts.ingestar_corpus [directorio_corpus]
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from servicio.contenedor import Contenedor  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent


def main(directorio: str | None = None) -> None:
    corpus = Path(directorio or RAIZ / "corpus" / "controles")
    c = Contenedor()
    print(f"Indexando corpus desde {corpus} con embeddings '{c.conf.embeddings.modelo}' "
          f"(proveedor {c.conf.proveedor_modelos})...")
    resultado = c.contexto.ingestar_corpus(corpus)
    archivos = sorted(corpus.glob("*.md"))
    firma = hashlib.sha256("".join(f"{a.name}{a.stat().st_size}" for a in archivos).encode()).hexdigest()
    c.docs.guardar_documento("corpus-controles", "NIST SP 800-53 Rev. 5 (controles base)", "md",
                             firma, resultado["fragmentos"], b"")
    print(f"Listo: {resultado['documentos']} controles, {resultado['fragmentos']} fragmentos. "
          f"Versión de corpus: {c.version_corpus()}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
