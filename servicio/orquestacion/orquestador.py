"""C2. Orquestación y patrones de agente.

Coordina el flujo completo de una consulta (análisis de una sección) a través de las capas inferiores,
siguiendo el flujo de la sección 4.2 del enunciado. Implementa el ciclo de agente: si la recuperación de
controles es pobre, el modelo reformula la consulta y se vuelve a buscar, hasta un máximo de iteraciones.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

from servicio.cache.cache import CacheConsultas
from servicio.config import Configuracion
from servicio.contexto import prompts
from servicio.contexto.rag import ConstructorContexto
from servicio.dominio import ErrorModelo, Hallazgo, Seccion
from servicio.guardrails import verificaciones
from servicio.modelos.enrutador import Enrutador
from servicio.modelos.gateway import GatewayModelos
from servicio.observabilidad.trazas import observador


@dataclass
class ResultadoSeccion:
    seccion: int
    titulo: str
    hallazgos: list[Hallazgo]
    resumen: str
    modelo: str
    ruta: str
    cache: str
    guardrails_entrada: str
    guardrails_salida: str
    iteraciones_agente: int
    fuentes: list[dict]
    bloqueada: bool = False
    mensaje: str | None = None
    metadatos: dict[str, Any] = field(default_factory=dict)


class Orquestador:
    def __init__(self, conf: Configuracion, contexto: ConstructorContexto, enrutador: Enrutador,
                 gateway: GatewayModelos, cache: CacheConsultas) -> None:
        self._conf = conf
        self._contexto = contexto
        self._enrutador = enrutador
        self._gateway = gateway
        self._cache = cache

    def analizar_seccion(self, seccion: Seccion, version_corpus: str) -> ResultadoSeccion:
        traza = observador.traza() or observador.nueva_traza()
        inicio = time.perf_counter()
        base = dict(seccion=seccion.indice, titulo=seccion.encabezado())

        # C3 guardrails de entrada
        entrada = verificaciones.verificar_entrada(f"{seccion.titulo}\n{seccion.texto}", self._conf.guardrails)
        if not entrada.aprobada:
            observador.registrar("orquestacion", "consulta_completada", (time.perf_counter() - inicio) * 1000,
                                 estado="bloqueada", iteraciones_agente=0)
            return ResultadoSeccion(**base, hallazgos=[], resumen="", modelo="", ruta="", cache="ninguna",
                                    guardrails_entrada="bloqueada", guardrails_salida="n/a", iteraciones_agente=0,
                                    fuentes=[], bloqueada=True, mensaje=entrada.mensaje_seguro)
        seccion_saneada = Seccion(seccion.indice, seccion.titulo, entrada.texto_saneado)

        # C6 enrutador
        decision = self._enrutador.clasificar(seccion_saneada)
        observador.registrar("modelos", "ruta", ruta=decision.ruta, puntaje=decision.puntaje, temas=decision.temas)

        # C4 caché (exacta/semántica) sobre el texto de la sección
        consulta = self._contexto.consulta_de_seccion(seccion_saneada)
        vector = self._contexto._embeber_consulta(consulta)
        en_cache = self._cache.buscar(consulta, vector, version_corpus)
        if en_cache.encontrada:
            r = en_cache.resultado
            observador.registrar("orquestacion", "consulta_completada", (time.perf_counter() - inicio) * 1000,
                                 estado="cache", iteraciones_agente=0)
            return ResultadoSeccion(**base, hallazgos=[Hallazgo(**h) for h in r["hallazgos"]], resumen=r["resumen"],
                                    modelo=r["modelo"], ruta=decision.ruta, cache=en_cache.tipo,
                                    guardrails_entrada="aprobada", guardrails_salida="aprobada (caché)",
                                    iteraciones_agente=0, fuentes=r["fuentes"],
                                    metadatos={"similitud_cache": en_cache.similitud})

        # C5 + C2 recuperación con ciclo de agente
        recuperacion = self._contexto.recuperar(consulta)
        iteraciones = 1
        umbral_pobre = self._conf.agente["umbral_recuperacion_pobre"]
        while recuperacion.pobre(umbral_pobre) and iteraciones < self._conf.agente["max_iteraciones"]:
            iteraciones += 1
            try:
                ref = self._gateway.generar(
                    [{"role": "system", "content": "Eres un asistente que reescribe consultas de búsqueda."},
                     {"role": "user", "content": prompts.prompt_reformulacion(consulta, iteraciones)}],
                    modelo=self._conf.modelos.modelo_reformulacion, esquema=prompts.ESQUEMA_REFORMULACION,
                    max_tokens=200, usar_respaldo=True)
                nueva = json.loads(ref.texto).get("consulta", "").strip()
            except (ErrorModelo, json.JSONDecodeError):
                nueva = ""
            observador.registrar("orquestacion", "reformulacion", iteracion=iteraciones, consulta_nueva=nueva[:120])
            if not nueva:
                break
            recuperacion = self._contexto.recuperar(nueva)

        fuentes_texto, refs = self._contexto.armar_fuentes(recuperacion.fragmentos)
        etiquetas = {r["etiqueta"] for r in refs}

        # C6 gateway -> modelo
        try:
            with observador.medir("orquestacion", "etapa", etapa="generacion"):
                respuesta = self._gateway.generar(
                    [{"role": "system", "content": prompts.SISTEMA_AUDITOR},
                     {"role": "user", "content": prompts.prompt_analisis(seccion_saneada, fuentes_texto)}],
                    ruta=decision.ruta, esquema=prompts.ESQUEMA_ANALISIS, usar_respaldo=True)
        except ErrorModelo as error:
            observador.registrar("orquestacion", "consulta_completada", (time.perf_counter() - inicio) * 1000,
                                 estado="error", iteraciones_agente=iteraciones)
            return ResultadoSeccion(**base, hallazgos=[], resumen="", modelo="", ruta=decision.ruta, cache="ninguna",
                                    guardrails_entrada="aprobada", guardrails_salida="error", iteraciones_agente=iteraciones,
                                    fuentes=refs, bloqueada=True,
                                    mensaje=f"No se pudo completar el análisis de la sección: {error}")

        # C3 guardrails de salida (con un reintento si el esquema es inválido)
        datos = self._parsear(respuesta.texto)
        ok, _res, politica = verificaciones.verificar_salida(datos, etiquetas)
        if not ok and politica == "reintentar":
            with observador.medir("orquestacion", "etapa", etapa="reintento_salida"):
                respuesta = self._gateway.generar(
                    [{"role": "system", "content": prompts.SISTEMA_AUDITOR},
                     {"role": "user", "content": prompts.prompt_analisis(seccion_saneada, fuentes_texto) +
                      "\n\nResponde SOLO con el objeto JSON válido indicado."}],
                    ruta=decision.ruta, esquema=prompts.ESQUEMA_ANALISIS, usar_respaldo=True)
            datos = self._parsear(respuesta.texto)
            ok, _res, politica = verificaciones.verificar_salida(datos, etiquetas)
        if not ok:
            datos = {"resumen": "No se obtuvo una respuesta válida del modelo.", "hallazgos": []}

        hallazgos = self._construir_hallazgos(datos, seccion_saneada, refs)
        resultado_dict = {
            "resumen": datos.get("resumen", ""), "modelo": respuesta.modelo,
            "hallazgos": [h.__dict__ for h in hallazgos], "fuentes": refs,
        }
        self._cache.guardar(consulta, vector, resultado_dict, version_corpus, ["corpus"])
        observador.registrar("orquestacion", "consulta_completada", (time.perf_counter() - inicio) * 1000,
                             estado="generada", iteraciones_agente=iteraciones, hallazgos=len(hallazgos),
                             modelo=respuesta.modelo, respaldo=respuesta.uso_respaldo)
        return ResultadoSeccion(**base, hallazgos=hallazgos, resumen=datos.get("resumen", ""),
                                modelo=respuesta.modelo, ruta=decision.ruta, cache="ninguna",
                                guardrails_entrada="aprobada", guardrails_salida="aprobada",
                                iteraciones_agente=iteraciones, fuentes=refs,
                                metadatos={"uso_respaldo": respuesta.uso_respaldo,
                                           "mejor_puntaje_recuperacion": round(recuperacion.mejor_puntaje, 4)})

    @staticmethod
    def _parsear(texto: str) -> dict | None:
        try:
            return json.loads(texto)
        except json.JSONDecodeError:
            inicio, fin = texto.find("{"), texto.rfind("}")
            if inicio != -1 and fin != -1:
                try:
                    return json.loads(texto[inicio:fin + 1])
                except json.JSONDecodeError:
                    return None
            return None

    def _construir_hallazgos(self, datos: dict, seccion: Seccion, refs: list[dict]) -> list[Hallazgo]:
        por_etiqueta = {r["etiqueta"]: r for r in refs}
        por_control = {r["control"]: r for r in refs}
        salida: list[Hallazgo] = []
        for h in datos.get("hallazgos", []):
            ref = por_etiqueta.get(h.get("fuente")) or por_control.get(h.get("control_id"), {})
            salida.append(Hallazgo(
                seccion=seccion.indice, seccion_titulo=seccion.encabezado(),
                control_id=h.get("control_id", ref.get("control", "")),
                funcion=ref.get("funcion", ""), estado=h.get("estado", "parcial"),
                gravedad=h.get("gravedad", "media"), descripcion=h.get("descripcion", ""),
                evidencia=h.get("evidencia", ""), recomendacion=h.get("recomendacion", ""),
                fuente={"control": ref.get("control", h.get("control_id", "")), "titulo": ref.get("titulo", ""),
                        "puntaje": ref.get("puntaje"), "fragmento_id": ref.get("fragmento_id")}))
        return salida
