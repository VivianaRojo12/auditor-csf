"""C4. Caché de dos niveles: exacta (hash) y semántica (similitud de embeddings).

- Exacta: misma sección y misma configuración -> llave por hash.
- Semántica: secciones parecidas -> se compara el embedding contra las entradas de la misma versión del
  corpus; si la similitud supera el umbral, se sirve la respuesta guardada.
Se invalida cuando cambian los documentos (por cambio de versión del corpus) y expira por TTL.
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass

import numpy as np

from servicio.datos.interfaces import AlmacenCache
from servicio.observabilidad.trazas import observador


@dataclass
class ResultadoCache:
    encontrada: bool
    tipo: str              # exacta | semantica | ninguna
    resultado: dict | None = None
    similitud: float | None = None


class CacheConsultas:
    def __init__(self, almacen: AlmacenCache, conf: dict, huella_config: str) -> None:
        self._almacen = almacen
        self._umbral = conf["umbral_semantico"]
        self._ttl_s = conf["ttl_horas"] * 3600
        self._huella = huella_config

    def _llave_exacta(self, texto: str, version_corpus: str) -> str:
        base = f"{self._huella}|{version_corpus}|{texto.strip()}"
        return hashlib.sha256(base.encode()).hexdigest()

    def buscar(self, texto: str, vector: list[float], version_corpus: str) -> ResultadoCache:
        with observador.medir("cache", "consulta") as m:
            self._almacen.purgar_expiradas(self._ttl_s)
            llave = self._llave_exacta(texto, version_corpus)
            exacta = self._almacen.obtener_exacta(llave)
            if exacta:
                m["resultado"] = "exacta"
                return ResultadoCache(True, "exacta", exacta["resultado"])
            mejor, mejor_sim = None, 0.0
            v = np.asarray(vector, dtype=np.float32)
            v /= (np.linalg.norm(v) or 1.0)
            for _llave, vec, resultado, _creada in self._almacen.candidatos_semanticos(version_corpus):
                u = np.asarray(vec, dtype=np.float32)
                sim = float(u @ v / ((np.linalg.norm(u) or 1.0)))
                if sim > mejor_sim:
                    mejor, mejor_sim = resultado, sim
            if mejor is not None and mejor_sim >= self._umbral:
                m["resultado"], m["similitud"] = "semantica", round(mejor_sim, 4)
                return ResultadoCache(True, "semantica", mejor, round(mejor_sim, 4))
            m["resultado"] = "ninguna"
            return ResultadoCache(False, "ninguna", similitud=round(mejor_sim, 4) if mejor is not None else None)

    def guardar(self, texto: str, vector: list[float], resultado: dict, version_corpus: str,
                documentos: list[str]) -> None:
        llave = self._llave_exacta(texto, version_corpus)
        self._almacen.guardar(llave, vector, resultado, version_corpus, documentos)

    def invalidar_documento(self, doc_id: str) -> int:
        n = self._almacen.invalidar_documento(doc_id)
        observador.registrar("cache", "invalidacion", doc_id=doc_id, entradas=n)
        return n

    def invalidar_por_version(self, version_vigente: str) -> int:
        return self._almacen.purgar_version(version_vigente)
