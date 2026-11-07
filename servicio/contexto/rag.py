"""C5. Construcción de contexto: ingesta del corpus, recuperación de controles y armado del prompt.

Es el corazón del RAG. Recupera, para cada sección de la política, los controles 800-53 más parecidos,
descarta los que no superan el umbral y arma el prompt con sus fuentes numeradas.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from servicio.config import Configuracion
from servicio.contexto.documentos import fragmentar_control
from servicio.datos.interfaces import BaseVectorial, ServidorModelos
from servicio.dominio import Fragmento, Seccion
from servicio.observabilidad.trazas import observador


@dataclass
class Recuperacion:
    fragmentos: list[Fragmento]
    mejor_puntaje: float
    consulta: str

    def pobre(self, umbral: float) -> bool:
        return not self.fragmentos or self.mejor_puntaje < umbral


class ConstructorContexto:
    def __init__(self, conf: Configuracion, servidor: ServidorModelos, base: BaseVectorial) -> None:
        self._conf = conf
        self._servidor = servidor
        self._base = base

    # --- ingesta del corpus de controles ---
    def ingestar_corpus(self, directorio: Path) -> dict:
        archivos = sorted(Path(directorio).glob("*.md"))
        fragmentos: list[Fragmento] = []
        for archivo in archivos:
            fragmentos.extend(fragmentar_control(archivo, self._conf.fragmentacion["tamano"],
                                                  self._conf.fragmentacion["solapamiento"]))
        self.indexar(fragmentos)
        observador.registrar("contexto", "ingesta_corpus", documentos=len(archivos), fragmentos=len(fragmentos))
        return {"documentos": len(archivos), "fragmentos": len(fragmentos)}

    def indexar(self, fragmentos: list[Fragmento]) -> None:
        if not fragmentos:
            return
        modelo = self._conf.embeddings.modelo
        prefijo = self._conf.embeddings.prefijo("documento")
        vectores: list[list[float]] = []
        lote = self._conf.embeddings.lote
        for i in range(0, len(fragmentos), lote):
            textos = [prefijo + f.texto for f in fragmentos[i:i + lote]]
            vectores.extend(self._servidor.embeber(modelo, textos))
        self._base.agregar(fragmentos, vectores)

    # --- recuperación ---
    def _embeber_consulta(self, texto: str) -> list[float]:
        prefijo = self._conf.embeddings.prefijo("consulta")
        return self._servidor.embeber(self._conf.embeddings.modelo, [prefijo + texto])[0]

    def recuperar(self, consulta: str) -> Recuperacion:
        with observador.medir("contexto", "recuperacion") as m:
            vector = self._embeber_consulta(consulta)
            k = self._conf.recuperacion["k"]
            umbral = self._conf.recuperacion["umbral"]
            crudos = self._base.buscar(vector, k)
            filtrados = [f for f in crudos if f.puntaje >= umbral]
            mejor = crudos[0].puntaje if crudos else 0.0
            m["recuperados"], m["sobre_umbral"], m["mejor_puntaje"] = len(crudos), len(filtrados), round(mejor, 4)
        return Recuperacion(fragmentos=filtrados, mejor_puntaje=mejor, consulta=consulta)

    def consulta_de_seccion(self, seccion: Seccion) -> str:
        return f"{seccion.titulo}. {seccion.texto}"[:1200]

    # --- armado del prompt ---
    def armar_fuentes(self, fragmentos: list[Fragmento]) -> tuple[str, list[dict]]:
        lineas, refs = [], []
        for i, f in enumerate(fragmentos[: self._conf.recuperacion["max_fragmentos_prompt"]], 1):
            etiqueta = f"F{i}"
            lineas.append(f"[{etiqueta}] {f.control} {f.metadatos.get('titulo', '')} "
                          f"(función {f.funcion}, puntaje {f.puntaje:.2f})\n{f.texto}")
            refs.append({"etiqueta": etiqueta, "control": f.control, "titulo": f.metadatos.get("titulo", ""),
                         "funcion": f.funcion, "puntaje": f.puntaje, "fragmento_id": f.id})
        return "\n\n".join(lineas), refs
