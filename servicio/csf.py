"""Taxonomía del NIST CSF 2.0 y su correspondencia con las familias de controles del SP 800-53 Rev. 5.

El CSF 2.0 organiza la ciberseguridad en seis funciones. El SP 800-53 agrupa los controles en familias.
Esta tabla es una correspondencia de trabajo (elaborada para este proyecto, no un crosswalk oficial de NIST)
que sirve para presentar los hallazgos del auditor agrupados por función del CSF.
"""
from __future__ import annotations

FUNCIONES: dict[str, str] = {
    "GV": "Gobernar",
    "ID": "Identificar",
    "PR": "Proteger",
    "DE": "Detectar",
    "RS": "Responder",
    "RC": "Recuperar",
}

# familia SP 800-53 -> función CSF 2.0 predominante
FAMILIA_A_FUNCION: dict[str, str] = {
    "pm": "GV", "pl": "GV", "ca": "GV", "sa": "GV", "sr": "GV",
    "ra": "ID", "cm": "ID", "pe": "ID",
    "ac": "PR", "at": "PR", "ia": "PR", "mp": "PR", "ps": "PR", "sc": "PR", "ma": "PR",
    "au": "DE", "si": "DE",
    "ir": "RS",
    "cp": "RC",
    "pt": "GV", "pa": "GV",
}

NOMBRE_FAMILIA: dict[str, str] = {
    "ac": "Control de acceso", "at": "Concientización y capacitación", "au": "Auditoría y rendición de cuentas",
    "ca": "Evaluación, autorización y monitoreo", "cm": "Gestión de la configuración",
    "cp": "Planeación de contingencias", "ia": "Identificación y autenticación", "ir": "Respuesta a incidentes",
    "ma": "Mantenimiento", "mp": "Protección de medios", "pe": "Protección física y ambiental",
    "pl": "Planeación", "pm": "Gestión del programa", "ps": "Seguridad del personal",
    "pt": "Transparencia y tratamiento de datos personales", "ra": "Evaluación de riesgos",
    "sa": "Adquisición de sistemas y servicios", "sc": "Protección de sistemas y comunicaciones",
    "si": "Integridad de sistemas e información", "sr": "Gestión de riesgos de la cadena de suministro",
}


def funcion_de_control(control_id: str) -> str:
    return FAMILIA_A_FUNCION.get(control_id.split("-")[0].lower(), "GV")


def nombre_funcion(codigo: str) -> str:
    return FUNCIONES.get(codigo, codigo)
