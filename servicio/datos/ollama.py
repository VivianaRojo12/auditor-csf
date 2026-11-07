"""C7. Adaptador hacia el servidor local de modelos Ollama (API HTTP en el puerto 11434)."""
from __future__ import annotations

import time
from typing import Any

import httpx

from servicio.dominio import RespuestaModelo


class AdaptadorOllama:
    def __init__(self, url: str) -> None:
        self._url = url.rstrip("/")

    def generar(self, modelo: str, mensajes: list[dict[str, str]], esquema: dict | None,
                tiempo_limite_s: float, opciones: dict[str, Any]) -> RespuestaModelo:
        cuerpo: dict[str, Any] = {"model": modelo, "messages": mensajes, "stream": False, "options": opciones,
                                  "keep_alive": "30m"}
        if esquema is not None:
            cuerpo["format"] = esquema
        inicio = time.perf_counter()
        respuesta = httpx.post(f"{self._url}/api/chat", json=cuerpo, timeout=tiempo_limite_s)
        respuesta.raise_for_status()
        datos = respuesta.json()
        return RespuestaModelo(
            texto=datos.get("message", {}).get("content", ""),
            modelo=modelo,
            tokens_entrada=datos.get("prompt_eval_count", 0),
            tokens_salida=datos.get("eval_count", 0),
            duracion_ms=(time.perf_counter() - inicio) * 1000,
        )

    def embeber(self, modelo: str, textos: list[str]) -> list[list[float]]:
        respuesta = httpx.post(f"{self._url}/api/embed", json={"model": modelo, "input": textos, "keep_alive": "30m"},
                               timeout=600)
        respuesta.raise_for_status()
        return respuesta.json()["embeddings"]

    def estado(self) -> dict[str, Any]:
        try:
            r = httpx.get(f"{self._url}/api/tags", timeout=5)
            r.raise_for_status()
            modelos = [m["name"] for m in r.json().get("models", [])]
            return {"disponible": True, "modelos_instalados": modelos}
        except httpx.HTTPError as error:
            return {"disponible": False, "error": str(error)}

    def detalles_modelo(self, modelo: str) -> dict[str, Any]:
        info: dict[str, Any] = {"modelo": modelo}
        try:
            r = httpx.post(f"{self._url}/api/show", json={"model": modelo}, timeout=20)
            r.raise_for_status()
            d = r.json()
            detalles = d.get("details", {})
            info.update({
                "parametros": detalles.get("parameter_size"),
                "cuantizacion": detalles.get("quantization_level"),
                "familia": detalles.get("family"),
                "licencia": (d.get("license") or "").strip().splitlines()[0][:120] if d.get("license") else None,
            })
            contexto = [v for k, v in d.get("model_info", {}).items() if k.endswith("context_length")]
            info["ventana_contexto"] = contexto[0] if contexto else None
            etiquetas = httpx.get(f"{self._url}/api/tags", timeout=10).json().get("models", [])
            tam = next((m.get("size") for m in etiquetas if m.get("name") == modelo), None)
            info["tamano_disco_gb"] = round(tam / 1e9, 2) if tam else None
            cargados = httpx.get(f"{self._url}/api/ps", timeout=10).json().get("models", [])
            mem = next((m.get("size") for m in cargados if m.get("name") == modelo), None)
            info["memoria_gb"] = round(mem / 1e9, 2) if mem else None
        except (httpx.HTTPError, ValueError) as error:
            info["error"] = str(error)
        return info
