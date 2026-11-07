"""C6. Enrutador: clasifica la complejidad de la auditoría y elige la ruta (y con ella el modelo).

Criterio explícito y barato (sin llamar a un modelo). Una sección corta y acotada se analiza con el
modelo pequeño y rápido; una sección larga o que toca varios temas de control va al modelo más capaz.
La decisión se toma por sección, porque cada sección se analiza por separado.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from servicio.dominio import Seccion

# términos que indican que una sección abarca varios dominios de control (mayor complejidad de análisis)
TEMAS = {
    "acceso": r"\b(acces[oa]|contraseñ|autenticaci|privilegi|cuenta|credencial|mfa|roles?)",
    "cifrado": r"\b(cifrad|encripta|criptograf|llave|certificad|tls|vpn)",
    "incidentes": r"\b(incidente|respuesta|forense|notificaci|contenci)",
    "continuidad": r"\b(respaldo|backup|recuperaci|contingencia|continuidad|desastre)",
    "monitoreo": r"\b(monitore|bitácora|registro de eventos|logs?|auditor[ií]a|siem|detecci)",
    "riesgos": r"\b(riesg|amenaz|vulnerabilidad|evaluaci[óo]n de)",
    "proveedores": r"\b(proveedor|tercero|cadena de suministro|contratista)",
    "fisico": r"\b(f[íi]sic|instalaci|acceso al sitio|data center|centro de datos|cámara)",
}


@dataclass
class DecisionRuta:
    ruta: str
    puntaje: int
    temas: list[str] = field(default_factory=list)
    criterio: str = ""


class Enrutador:
    def __init__(self, umbral_complejidad: int) -> None:
        self.umbral = umbral_complejidad

    def clasificar(self, seccion: Seccion) -> DecisionRuta:
        texto = f"{seccion.titulo}\n{seccion.texto}".lower()
        temas = [n for n, patron in TEMAS.items() if re.search(patron, texto)]
        puntaje = len(temas)
        palabras = len(seccion.texto.split())
        if palabras >= 250:
            temas.append("extensión>=250")
            puntaje += 1
        if palabras >= 500:
            temas.append("extensión>=500")
            puntaje += 1
        ruta = "compleja" if puntaje >= self.umbral else "simple"
        return DecisionRuta(ruta=ruta, puntaje=puntaje, temas=temas,
                            criterio=f"{puntaje} señales de complejidad {'>=' if ruta == 'compleja' else '<'} "
                                     f"umbral {self.umbral}")
