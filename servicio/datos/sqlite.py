"""C7. Adaptadores sobre SQLite: documentos, caché, eventos de observabilidad y retroalimentación.

Cada recurso tiene su propio adaptador; comparten solo la utilidad de conexión.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np


class _Conexion:
    def __init__(self, ruta: Path, esquema: str) -> None:
        self._con = sqlite3.connect(str(ruta), check_same_thread=False)
        self._con.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._con.executescript(esquema)
            self._con.commit()

    def ejecutar(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with self._lock:
            cur = self._con.execute(sql, params)
            self._con.commit()
            return cur

    def consultar(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(r) for r in self._con.execute(sql, params).fetchall()]


class AlmacenDocumentosSQLite:
    def __init__(self, directorio: Path) -> None:
        self._dir = directorio / "documentos"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._db = _Conexion(directorio / "documentos.db", """
            CREATE TABLE IF NOT EXISTS documentos (
                id TEXT PRIMARY KEY, nombre TEXT, formato TEXT, sha256 TEXT, fragmentos INTEGER, fecha TEXT);
        """)

    def guardar_documento(self, doc_id: str, nombre: str, formato: str, sha256: str,
                          fragmentos: int, contenido: bytes) -> None:
        (self._dir / f"{doc_id}.{formato}").write_bytes(contenido)
        self._db.ejecutar("INSERT OR REPLACE INTO documentos VALUES (?,?,?,?,?,?)",
                          (doc_id, nombre, formato, sha256, fragmentos, time.strftime("%Y-%m-%dT%H:%M:%S")))

    def listar_documentos(self) -> list[dict[str, Any]]:
        return self._db.consultar("SELECT * FROM documentos ORDER BY nombre")

    def obtener_documento(self, doc_id: str) -> dict[str, Any] | None:
        filas = self._db.consultar("SELECT * FROM documentos WHERE id=?", (doc_id,))
        return filas[0] if filas else None

    def buscar_por_hash(self, sha256: str) -> dict[str, Any] | None:
        filas = self._db.consultar("SELECT * FROM documentos WHERE sha256=?", (sha256,))
        return filas[0] if filas else None

    def eliminar_documento(self, doc_id: str) -> bool:
        doc = self.obtener_documento(doc_id)
        if not doc:
            return False
        (self._dir / f"{doc_id}.{doc['formato']}").unlink(missing_ok=True)
        self._db.ejecutar("DELETE FROM documentos WHERE id=?", (doc_id,))
        return True

    def version_corpus(self) -> str:
        filas = self._db.consultar("SELECT id, sha256 FROM documentos ORDER BY id")
        return hashlib.sha256("".join(f"{f['id']}{f['sha256']}" for f in filas).encode()).hexdigest()[:12]


class AlmacenCacheSQLite:
    def __init__(self, directorio: Path) -> None:
        self._db = _Conexion(directorio / "cache.db", """
            CREATE TABLE IF NOT EXISTS cache (
                llave TEXT PRIMARY KEY, vector BLOB, resultado TEXT, version_corpus TEXT,
                documentos TEXT, creada REAL);
        """)

    def obtener_exacta(self, llave: str) -> dict[str, Any] | None:
        filas = self._db.consultar("SELECT resultado, creada FROM cache WHERE llave=?", (llave,))
        if not filas:
            return None
        return {"resultado": json.loads(filas[0]["resultado"]), "creada": filas[0]["creada"]}

    def guardar(self, llave: str, vector: list[float] | None, resultado: dict[str, Any],
                version_corpus: str, documentos: list[str]) -> None:
        blob = np.asarray(vector, dtype=np.float32).tobytes() if vector is not None else None
        self._db.ejecutar("INSERT OR REPLACE INTO cache VALUES (?,?,?,?,?,?)",
                          (llave, blob, json.dumps(resultado, ensure_ascii=False), version_corpus,
                           json.dumps(sorted(set(documentos))), time.time()))

    def candidatos_semanticos(self, version_corpus: str) -> list[tuple[str, list[float], dict[str, Any], float]]:
        filas = self._db.consultar(
            "SELECT llave, vector, resultado, creada FROM cache WHERE version_corpus=? AND vector IS NOT NULL",
            (version_corpus,))
        return [(f["llave"], np.frombuffer(f["vector"], dtype=np.float32).tolist(), json.loads(f["resultado"]),
                 f["creada"]) for f in filas]

    def invalidar_documento(self, doc_id: str) -> int:
        filas = self._db.consultar("SELECT llave, documentos FROM cache")
        afectadas = [f["llave"] for f in filas if doc_id in json.loads(f["documentos"] or "[]")]
        for llave in afectadas:
            self._db.ejecutar("DELETE FROM cache WHERE llave=?", (llave,))
        return len(afectadas)

    def purgar_version(self, version_vigente: str) -> int:
        return self._db.ejecutar("DELETE FROM cache WHERE version_corpus<>?", (version_vigente,)).rowcount

    def purgar_expiradas(self, ttl_s: float) -> int:
        return self._db.ejecutar("DELETE FROM cache WHERE creada<?", (time.time() - ttl_s,)).rowcount

    def contar(self) -> int:
        return self._db.consultar("SELECT COUNT(*) AS n FROM cache")[0]["n"]

    def vaciar(self) -> None:
        self._db.ejecutar("DELETE FROM cache")


def _percentil(valores: list[float], p: float) -> float:
    return round(float(np.percentile(valores, p)), 1) if valores else 0.0


class AlmacenEventosSQLite:
    def __init__(self, directorio: Path) -> None:
        self._db = _Conexion(directorio / "observabilidad.db", """
            CREATE TABLE IF NOT EXISTS eventos (
                id INTEGER PRIMARY KEY AUTOINCREMENT, traza_id TEXT, capa TEXT, evento TEXT,
                duracion_ms REAL, datos TEXT, ts REAL);
            CREATE INDEX IF NOT EXISTS idx_traza ON eventos(traza_id);
        """)

    def guardar_evento(self, evento: dict[str, Any]) -> None:
        self._db.ejecutar("INSERT INTO eventos (traza_id, capa, evento, duracion_ms, datos, ts) VALUES (?,?,?,?,?,?)",
                          (evento["traza_id"], evento["capa"], evento["evento"], evento["duracion_ms"],
                           json.dumps(evento["datos"], ensure_ascii=False, default=str), evento["ts"]))

    def eventos_de_traza(self, traza_id: str) -> list[dict[str, Any]]:
        filas = self._db.consultar("SELECT capa, evento, duracion_ms, datos, ts FROM eventos WHERE traza_id=? ORDER BY id",
                                   (traza_id,))
        for f in filas:
            f["datos"] = json.loads(f["datos"])
        return filas

    def resumen_metricas(self) -> dict[str, Any]:
        filas = self._db.consultar("SELECT traza_id, capa, evento, duracion_ms, datos FROM eventos")
        latencias: dict[str, list[float]] = defaultdict(list)
        cache: dict[str, int] = defaultdict(int)
        guardrails: dict[str, dict[str, int]] = defaultdict(lambda: {"evaluaciones": 0, "activaciones": 0})
        modelos: dict[str, dict[str, Any]] = defaultdict(lambda: {"llamadas": 0, "errores": 0, "latencias": [],
                                                                    "tokens_salida": 0})
        rutas: dict[str, int] = defaultdict(int)
        respaldos = 0
        iteraciones: list[int] = []
        totales: list[float] = []
        estados: dict[str, int] = defaultdict(int)
        for f in filas:
            datos = json.loads(f["datos"])
            clave = f"{f['capa']}.{f['evento']}"
            if f["duracion_ms"] is not None and f["evento"] in {"etapa", "llamada", "recuperacion", "consulta_completada"}:
                etiqueta = datos.get("etapa", f["capa"]) if f["evento"] == "etapa" else clave
                latencias[etiqueta].append(f["duracion_ms"])
            if clave == "cache.consulta":
                cache[datos.get("resultado", "ninguna")] += 1
            elif clave == "guardrails.verificacion":
                g = guardrails[datos.get("verificacion", "?")]
                g["evaluaciones"] += 1
                g["activaciones"] += 0 if datos.get("aprobada") else 1
            elif clave == "modelos.llamada":
                m = modelos[datos.get("modelo", "?")]
                m["llamadas"] += 1
                m["latencias"].append(f["duracion_ms"] or 0)
                m["tokens_salida"] += datos.get("tokens_salida", 0)
            elif clave == "modelos.error":
                modelos[datos.get("modelo", "?")]["errores"] += 1
            elif clave == "modelos.respaldo":
                respaldos += 1
            elif clave == "modelos.ruta":
                rutas[datos.get("ruta", "?")] += 1
            elif clave == "orquestacion.consulta_completada":
                totales.append(f["duracion_ms"] or 0)
                iteraciones.append(datos.get("iteraciones_agente", 0))
                estados[datos.get("estado", "?")] += 1
        consultas_cache = sum(cache.values())
        return {
            "consultas": {"total": len(totales), "por_estado": dict(estados),
                          "latencia_ms": {"promedio": round(float(np.mean(totales)), 1) if totales else 0,
                                          "p95": _percentil(totales, 95), "max": round(max(totales), 1) if totales else 0}},
            "latencia_por_capa_ms": {
                k: {"n": len(v), "promedio": round(float(np.mean(v)), 1), "p95": _percentil(v, 95), "max": round(max(v), 1)}
                for k, v in sorted(latencias.items())},
            "cache": {"por_tipo": dict(cache),
                      "tasa_aciertos": round((cache.get("exacta", 0) + cache.get("semantica", 0)) / consultas_cache, 3)
                      if consultas_cache else None},
            "guardrails": dict(guardrails),
            "modelos": {k: {"llamadas": v["llamadas"], "errores": v["errores"], "tokens_salida": v["tokens_salida"],
                            "latencia_promedio_ms": round(float(np.mean(v["latencias"])), 1) if v["latencias"] else 0}
                        for k, v in modelos.items()},
            "enrutador": {"por_ruta": dict(rutas), "usos_respaldo": respaldos},
            "agente": {"iteraciones_promedio": round(float(np.mean(iteraciones)), 2) if iteraciones else 0,
                       "consultas_con_reformulacion": sum(1 for i in iteraciones if i > 1)},
        }


class AlmacenRetroalimentacionSQLite:
    def __init__(self, directorio: Path) -> None:
        self._db = _Conexion(directorio / "retroalimentacion.db", """
            CREATE TABLE IF NOT EXISTS retroalimentacion (
                id INTEGER PRIMARY KEY AUTOINCREMENT, traza_id TEXT, util INTEGER, comentario TEXT,
                origen TEXT, ts TEXT);
        """)

    def guardar_retroalimentacion(self, traza_id: str, util: bool, comentario: str | None, origen: str) -> int:
        cur = self._db.ejecutar("INSERT INTO retroalimentacion (traza_id, util, comentario, origen, ts) VALUES (?,?,?,?,?)",
                                (traza_id, int(util), comentario, origen, time.strftime("%Y-%m-%dT%H:%M:%S")))
        return int(cur.lastrowid)

    def listar_retroalimentacion(self) -> list[dict[str, Any]]:
        return self._db.consultar("SELECT * FROM retroalimentacion ORDER BY id")
