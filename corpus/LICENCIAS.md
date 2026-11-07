# Origen y licencia del corpus

## Controles de referencia (base de conocimiento del auditor)

- **Fuente:** NIST Special Publication 800-53 Rev. 5 (catálogo de controles de seguridad y privacidad),
  publicado por el National Institute of Standards and Technology de los Estados Unidos.
- **Formato de origen:** OSCAL JSON del repositorio oficial `usnistgov/oscal-content`.
- **Licencia:** Dominio público. Como obra del gobierno de los Estados Unidos, está en el dominio público
  dentro de EE. UU.; además se dedica al dominio público mundial mediante CC0 1.0 Universal.
- **Procesamiento:** `scripts/construir_corpus_80053.py` extrae el enunciado y la guía de cada control base
  (se omiten las mejoras de control) y lo convierte a Markdown, uno por control, con la función del CSF 2.0
  asociada a su familia. Son 301 documentos.

## Marco de organización

- **NIST Cybersecurity Framework (CSF) 2.0:** se usa únicamente su taxonomía de seis funciones
  (Gobernar, Identificar, Proteger, Detectar, Responder, Recuperar) para agrupar los hallazgos. La
  correspondencia familia 800-53 → función CSF (`servicio/csf.py`) se elaboró para este proyecto y no es
  un crosswalk oficial de NIST.

## Documentos de prueba

Las políticas y procedimientos que se auditan en la demostración y en la evaluación
(`corpus/propios/`, `evaluacion/datos/`) son documentos ficticios creados para este proyecto. No
pertenecen a ninguna organización real y no contienen datos personales reales.
