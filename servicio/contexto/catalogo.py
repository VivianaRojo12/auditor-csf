"""C5. Catálogo de controles y cuestionarios de práctica.

Lee los controles del corpus (un Markdown por control) para mostrarlos en la web y arma preguntas de opción
múltiple usando solo datos oficiales del NIST SP 800-53: identificador, nombre, familia y texto del control.
No interviene ningún modelo: la respuesta correcta siempre es un dato del corpus.
La función del CSF de cada control viene de la correspondencia de trabajo de servicio/csf.py (no oficial), por
eso las preguntas nunca la usan.
"""
from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from pathlib import Path

from servicio.csf import NOMBRE_FAMILIA, funcion_de_control, nombre_funcion

_TITULO = re.compile(r"^#\s+([A-Z]{2}-\d+)\s+(.+?)\s*$")
_VINETA = re.compile(r"^(\s*)-\s+(.*)$")


@dataclass
class Control:
    id: str
    nombre: str
    familia: str            # sigla en mayúsculas, p. ej. "AC"
    texto: list[dict] = field(default_factory=list)   # [{"nivel": 0, "linea": "a. Define ..."}]

    @property
    def familia_nombre(self) -> str:
        return NOMBRE_FAMILIA.get(self.familia.lower(), self.familia)

    @property
    def funcion(self) -> str:
        return funcion_de_control(self.id)

    def requisito_principal(self) -> str:
        """Primera frase del control sin su viñeta ("a. ..."), útil como pista en una pregunta."""
        for t in self.texto:
            linea = re.sub(r"^[a-z0-9]+\.\s+", "", t["linea"])
            if len(linea) > 25:
                return linea
        return ""

    def resumen(self) -> dict:
        return {"id": self.id, "nombre": self.nombre, "familia": self.familia,
                "familia_nombre": self.familia_nombre, "funcion": self.funcion,
                "funcion_nombre": nombre_funcion(self.funcion)}

    def detalle(self) -> dict:
        return {**self.resumen(), "texto": self.texto,
                "fuente": "NIST SP 800-53 Rev. 5 (dominio público)"}


def _orden(control_id: str) -> tuple[str, int]:
    familia, numero = control_id.split("-")
    return familia, int(numero)


def leer_control(ruta: Path) -> Control | None:
    lineas = ruta.read_text(encoding="utf-8").splitlines()
    if not lineas or not (m := _TITULO.match(lineas[0])):
        return None
    control = Control(id=m.group(1), nombre=m.group(2), familia=m.group(1).split("-")[0])
    en_control = False
    for linea in lineas[1:]:
        if linea.startswith("## "):
            en_control = linea.strip().lower() == "## control"
            continue
        if not en_control or not linea.strip():
            continue
        v = _VINETA.match(linea)
        if v:
            control.texto.append({"nivel": max(0, len(v.group(1)) // 2 - 1), "linea": v.group(2).strip()})
        else:
            control.texto.append({"nivel": 0, "linea": linea.strip()})
    return control


class Catalogo:
    def __init__(self, directorio: Path) -> None:
        self._directorio = directorio
        self._controles: dict[str, Control] | None = None

    @property
    def controles(self) -> dict[str, Control]:
        if self._controles is None:   # carga perezosa: el corpus no cambia mientras corre el servicio
            leidos = [leer_control(p) for p in sorted(self._directorio.glob("*.md"))]
            self._controles = {c.id: c for c in sorted((c for c in leidos if c), key=lambda c: _orden(c.id))}
        return self._controles

    def listar(self, familia: str | None = None, texto: str | None = None) -> list[dict]:
        q = (texto or "").strip().lower()
        fam = (familia or "").strip().upper()
        return [c.resumen() for c in self.controles.values()
                if (not fam or c.familia == fam) and (not q or q in c.id.lower() or q in c.nombre.lower())]

    def obtener(self, control_id: str) -> Control | None:
        return self.controles.get(control_id.strip().upper())

    def familias(self) -> list[dict]:
        conteo: dict[str, int] = {}
        for c in self.controles.values():
            conteo[c.familia] = conteo.get(c.familia, 0) + 1
        return [{"familia": f, "nombre": NOMBRE_FAMILIA.get(f.lower(), f), "controles": n}
                for f, n in sorted(conteo.items())]

    # --- Cuestionarios -------------------------------------------------------------------------------
    def cuestionario(self, familia: str | None = None, n: int = 10, semilla: int | None = None) -> dict:
        """Arma `n` preguntas de opción múltiple (4 opciones) con datos oficiales del corpus."""
        azar = random.Random(semilla)
        fam = (familia or "").strip().upper() or None
        candidatos = [c for c in self.controles.values() if not fam or c.familia == fam]
        if len(candidatos) < 4:
            raise ValueError("La familia necesita al menos 4 controles para armar preguntas.")
        elegidos = azar.sample(candidatos, k=min(n, len(candidatos)))
        tipos = ["nombre_a_id", "id_a_nombre", "requisito_a_id"] + ([] if fam else ["id_a_familia"])
        preguntas = []
        repetidos = self._requisitos_repetidos()
        for i, c in enumerate(elegidos):
            tipo = tipos[i % len(tipos)]
            # un requisito compartido por varios controles (p. ej., los "-1" de cada familia) no identifica a uno solo
            if tipo == "requisito_a_id" and (not c.requisito_principal() or c.requisito_principal() in repetidos):
                tipo = "nombre_a_id"
            preguntas.append(self._pregunta(c, tipo, candidatos, azar))
        return {"familia": fam, "familia_nombre": NOMBRE_FAMILIA.get(fam.lower(), fam) if fam else "Todas las familias",
                "preguntas": preguntas}

    def _pregunta(self, c: Control, tipo: str, candidatos: list[Control], azar: random.Random) -> dict:
        # opciones incorrectas de la misma familia cuando alcanzan, para que la sigla no delate la respuesta
        misma = [o for o in self.controles.values() if o.familia == c.familia and o.id != c.id]
        otros = misma if len(misma) >= 3 else [o for o in candidatos if o.id != c.id]
        if tipo == "id_a_familia":
            correcta = f"{c.familia} – {c.familia_nombre}"
            familias = sorted({o.familia for o in self.controles.values() if o.familia != c.familia})
            distractores = [f"{f} – {NOMBRE_FAMILIA.get(f.lower(), f)}" for f in azar.sample(familias, 3)]
            enunciado = f"¿A qué familia pertenece el control {c.id}?"
            idioma = "es"
        elif tipo == "id_a_nombre":
            correcta = c.nombre
            distractores = self._distintos([o.nombre for o in otros], correcta, azar)
            enunciado = f"¿Cómo se llama el control {c.id}?"
            idioma = "en"
        elif tipo == "requisito_a_id":
            correcta = c.id
            distractores = [o.id for o in azar.sample(otros, 3)]
            enunciado = f"¿A qué control corresponde este requisito? «{c.requisito_principal()}»"
            idioma = "es"
        else:  # nombre_a_id: la familia va en el enunciado y ningún distractor comparte el nombre
            correcta = c.id
            con_otro_nombre = [o for o in otros if o.nombre != c.nombre]
            if len(con_otro_nombre) < 3:
                con_otro_nombre = [o for o in candidatos if o.id != c.id and o.nombre != c.nombre]
            distractores = [o.id for o in azar.sample(con_otro_nombre, 3)]
            enunciado = f"En la familia {c.familia_nombre}, ¿qué control se llama «{c.nombre}»?"
            idioma = "es"
        opciones = distractores + [correcta]
        azar.shuffle(opciones)
        return {"tipo": tipo, "control": c.id, "enunciado": enunciado, "opciones": opciones,
                "opciones_idioma": idioma, "correcta": opciones.index(correcta),
                "explicacion": {"control": c.id, "nombre": c.nombre, "familia": c.familia,
                                "familia_nombre": c.familia_nombre, "requisito": c.requisito_principal()}}

    def _requisitos_repetidos(self) -> set[str]:
        vistos: dict[str, int] = {}
        for c in self.controles.values():
            r = c.requisito_principal()
            vistos[r] = vistos.get(r, 0) + 1
        return {r for r, n in vistos.items() if n > 1}

    @staticmethod
    def _distintos(valores: list[str], excluir: str, azar: random.Random) -> list[str]:
        """Tres valores distintos entre sí y distintos de la respuesta (hay nombres repetidos entre familias)."""
        unicos = sorted({v for v in valores if v != excluir})
        return azar.sample(unicos, 3)
