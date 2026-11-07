"""C7. Adaptador simulado del servidor de modelos.

Solo para pruebas automáticas sin Ollama: produce embeddings deterministas por n-gramas y respuestas JSON
válidas construidas a partir del contexto del prompt. No se usa en la demostración ni en la evaluación.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import time
from typing import Any

from servicio.dominio import RespuestaModelo

DIM = 384


def _vector(texto: str) -> list[float]:
    v = [0.0] * DIM
    t = f"  {texto.lower()}  "
    for n in (3, 4):
        for i in range(len(t) - n + 1):
            h = int(hashlib.md5(t[i:i + n].encode()).hexdigest()[:8], 16)
            v[h % DIM] += 1.0 if (h >> 9) & 1 else -1.0
    norma = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / norma for x in v]


class AdaptadorSimulado:
    def __init__(self, latencia_s: float = 0.0, fallar_modelos: set[str] | None = None) -> None:
        self.latencia_s = latencia_s
        self.fallar_modelos = fallar_modelos or set()

    def embeber(self, modelo: str, textos: list[str]) -> list[list[float]]:
        return [_vector(t) for t in textos]

    def generar(self, modelo: str, mensajes: list[dict[str, str]], esquema: dict | None,
                tiempo_limite_s: float, opciones: dict[str, Any]) -> RespuestaModelo:
        if modelo in self.fallar_modelos:
            raise TimeoutError(f"modelo simulado {modelo} sin respuesta")
        time.sleep(self.latencia_s)
        prompt = mensajes[-1]["content"]
        propiedades = (esquema or {}).get("properties", {})
        if "consulta" in propiedades and "hallazgos" not in propiedades:
            salida = {"consulta": "controles de seguridad relacionados", "razon": "reformulación simulada"}
        elif "puntaje" in propiedades:
            salida = {"puntaje": 4, "justificacion": "Evaluación simulada de fidelidad."}
        else:
            # Extrae las fuentes recuperadas del prompt: "[F1] AC-2 Título (función PR, puntaje ...)"
            fuentes = re.findall(r"\[(F\d+)\]\s+([A-Z]{2}-\d+)", prompt)
            hallazgos = []
            for i, (fid, control) in enumerate(fuentes[:4]):
                estado = ["cubierto", "parcial", "ausente"][i % 3]
                hallazgos.append({
                    "control_id": control, "estado": estado,
                    "gravedad": ["alta", "media", "baja"][i % 3],
                    "descripcion": f"Correspondencia simulada con el control {control}.",
                    "evidencia": "" if estado == "ausente" else "fragmento citado de la sección",
                    "recomendacion": f"Alinear la redacción con {control} (recomendación simulada).",
                    "fuente": fid})
            salida = {"resumen": "Resumen simulado de la sección auditada.", "hallazgos": hallazgos}
        texto = json.dumps(salida, ensure_ascii=False)
        return RespuestaModelo(texto=texto, modelo=modelo, tokens_entrada=len(prompt) // 4,
                               tokens_salida=len(texto) // 4, duracion_ms=self.latencia_s * 1000)

    def estado(self) -> dict[str, Any]:
        return {"disponible": True, "modelos_instalados": ["simulado"], "nota": "proveedor simulado"}

    def detalles_modelo(self, modelo: str) -> dict[str, Any]:
        return {"modelo": modelo, "parametros": "n/d", "cuantizacion": "n/d"}
