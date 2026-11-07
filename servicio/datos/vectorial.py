"""C7. Adaptadores de base vectorial: ChromaDB persistente y una alternativa en memoria con NumPy.

Ambos implementan la interfaz BaseVectorial; el resto del servicio no sabe cuál está en uso.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from servicio.dominio import Fragmento


def _normalizar(vectores: list[list[float]]) -> np.ndarray:
    m = np.asarray(vectores, dtype=np.float32)
    normas = np.linalg.norm(m, axis=1, keepdims=True)
    normas[normas == 0] = 1.0
    return m / normas


class VectorialChroma:
    def __init__(self, directorio: Path, coleccion: str) -> None:
        import chromadb
        from chromadb.config import Settings

        self._cliente = chromadb.PersistentClient(path=str(directorio), settings=Settings(anonymized_telemetry=False))
        self._nombre = coleccion
        self._col = self._cliente.get_or_create_collection(coleccion, metadata={"hnsw:space": "cosine"})

    def agregar(self, fragmentos: list[Fragmento], vectores: list[list[float]]) -> None:
        if not fragmentos:
            return
        normalizados = _normalizar(vectores).tolist()
        for i in range(0, len(fragmentos), 500):
            lote = fragmentos[i:i + 500]
            self._col.upsert(
                ids=[f.id for f in lote],
                documents=[f.texto for f in lote],
                metadatas=[{k: v for k, v in f.metadatos.items() if v is not None} for f in lote],
                embeddings=normalizados[i:i + 500],
            )

    def buscar(self, vector: list[float], k: int, filtro: dict | None = None) -> list[Fragmento]:
        if self._col.count() == 0:
            return []
        consulta = _normalizar([vector]).tolist()
        r = self._col.query(query_embeddings=consulta, n_results=min(k, self._col.count()), where=filtro or None)
        return [
            Fragmento(id=i, texto=t, metadatos=m or {}, puntaje=round(1.0 - float(d), 4))
            for i, t, m, d in zip(r["ids"][0], r["documents"][0], r["metadatas"][0], r["distances"][0])
        ]

    def eliminar_documento(self, doc_id: str) -> int:
        existentes = self._col.get(where={"doc_id": doc_id}, include=[])
        if existentes["ids"]:
            self._col.delete(ids=existentes["ids"])
        return len(existentes["ids"])

    def contar(self) -> int:
        return self._col.count()

    def obtener(self, ids: list[str]) -> list[Fragmento]:
        r = self._col.get(ids=ids, include=["documents", "metadatas"])
        return [Fragmento(id=i, texto=t, metadatos=m or {}) for i, t, m in zip(r["ids"], r["documents"], r["metadatas"])]

    def estado(self) -> dict[str, Any]:
        return {"tipo": "chroma", "coleccion": self._nombre, "fragmentos": self._col.count(), "disponible": True}


class VectorialMemoria:
    def __init__(self) -> None:
        self._fragmentos: list[Fragmento] = []
        self._matriz = np.zeros((0, 0), dtype=np.float32)

    def agregar(self, fragmentos: list[Fragmento], vectores: list[list[float]]) -> None:
        if not fragmentos:
            return
        nuevos = _normalizar(vectores)
        ids = {f.id for f in fragmentos}
        conservar = [i for i, f in enumerate(self._fragmentos) if f.id not in ids]
        self._fragmentos = [self._fragmentos[i] for i in conservar] + list(fragmentos)
        base = self._matriz[conservar] if len(conservar) else np.zeros((0, nuevos.shape[1]), dtype=np.float32)
        self._matriz = np.vstack([base, nuevos])

    def buscar(self, vector: list[float], k: int, filtro: dict | None = None) -> list[Fragmento]:
        if not self._fragmentos:
            return []
        sims = self._matriz @ _normalizar([vector])[0]
        orden = np.argsort(-sims)
        salida = []
        for i in orden:
            f = self._fragmentos[int(i)]
            if filtro and any(f.metadatos.get(c) != v for c, v in filtro.items()):
                continue
            salida.append(Fragmento(id=f.id, texto=f.texto, metadatos=f.metadatos, puntaje=round(float(sims[i]), 4)))
            if len(salida) == k:
                break
        return salida

    def eliminar_documento(self, doc_id: str) -> int:
        conservar = [i for i, f in enumerate(self._fragmentos) if f.metadatos.get("doc_id") != doc_id]
        eliminados = len(self._fragmentos) - len(conservar)
        self._fragmentos = [self._fragmentos[i] for i in conservar]
        self._matriz = self._matriz[conservar] if conservar else np.zeros((0, self._matriz.shape[1] if self._matriz.size else 0), dtype=np.float32)
        return eliminados

    def contar(self) -> int:
        return len(self._fragmentos)

    def obtener(self, ids: list[str]) -> list[Fragmento]:
        buscados = set(ids)
        return [f for f in self._fragmentos if f.id in buscados]

    def estado(self) -> dict[str, Any]:
        return {"tipo": "memoria", "fragmentos": len(self._fragmentos), "disponible": True}
