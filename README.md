# Auditor de políticas de seguridad contra NIST CSF 2.0

Servicio en capas con embeddings y RAG que audita una política o procedimiento de seguridad de la
información contra los controles del **NIST SP 800-53 Rev. 5** y presenta los hallazgos agrupados por las
seis funciones del **NIST CSF 2.0** (Gobernar, Identificar, Proteger, Detectar, Responder, Recuperar).

El producto no es un chatbot: recibe un documento y entrega un **informe de brechas** con el estado de cada
control (cubierto, parcial, ausente), su gravedad, la evidencia citada del documento, el control de
referencia y una redacción corregida. Existe una consulta secundaria para preguntar sobre los controles.

## Qué resuelve

Un responsable de seguridad de una organización de infraestructura crítica compara sus documentos contra un
marco de control. Hacerlo a mano exige leer cientos de controles y cruzarlos con cada párrafo. El sistema
recupera, para cada sección, los controles pertinentes y marca las brechas con su fuente.

## Arquitectura

Dos contenedores: la **aplicación web** (capa de presentación) y el **servicio** (lógica de negocio). El
servicio se organiza en capas; cada capa solo usa a las de abajo por interfaces. Ver `docs/`.

```
proyecto/
  web/              Capa de presentación (HTML+JS); consume solo la API por HTTP
  servicio/
    api/            C1  Interfaz del servicio (FastAPI, OpenAPI)
    orquestacion/   C2  Flujo de consulta y ciclo de agente
    guardrails/     C3  Verificaciones de entrada y salida
    cache/          C4  Caché exacta y semántica
    contexto/       C5  RAG, lectura de documentos y armado del prompt
    modelos/        C6  Enrutador y gateway de modelos
    datos/          C7  Adaptadores: Ollama, base vectorial, SQLite
    observabilidad/ T1  Trazas, bitácoras y métricas
    retroalimentacion/ T2  Opinión del usuario ligada a la traza
  corpus/           Controles SP 800-53 Rev. 5 (base de conocimiento)
  evaluacion/       Conjuntos de prueba, experimentos y resultados
  docs/             Diagramas (C4 y UML) y ADR
  scripts/          Construcción del corpus e ingesta
  tests/            Pruebas de integración (proveedor simulado, sin Ollama)
```

## Requisitos

- Python 3.11 o superior.
- [Ollama](https://ollama.com) en ejecución local.
- Modelos (se descargan una vez):

```
ollama pull qwen2.5:7b
ollama pull qwen2.5:3b
ollama pull llama3.2:3b
ollama pull nomic-embed-text
ollama pull bge-m3
```

## Instalación y ejecución

```bash
python -m venv .venv && source .venv/bin/activate   # en Windows: .venv\Scripts\activate
pip install -r requisitos.txt

# 1. Construir el corpus desde el catálogo oficial (ver scripts/ para el origen de datos)
python scripts/construir_corpus_80053.py RUTA/NIST_SP-800-53_rev5_catalog.json corpus/controles

# 2. Indexar el corpus en la base vectorial
python -m scripts.ingestar_corpus

# 3. Levantar el servicio (API en http://127.0.0.1:8000, OpenAPI en /docs)
python -m servicio.main

# 4. En otra terminal, levantar la aplicación web (http://127.0.0.1:8080)
python web/servidor_web.py 8080 http://127.0.0.1:8000
```

Abre `http://127.0.0.1:8080`, carga una política (hay una de ejemplo) y revisa el informe.

## Evaluación

Ejecuta los experimentos de selección de modelos y la evaluación del sistema (requiere Ollama):

```bash
python -m evaluacion.ejecutar_todo
```

Esto elige el modelo de embeddings y los modelos de cada ruta, **calibra `config.yaml`**, reindexa el
corpus y escribe los resultados en `evaluacion/resultados/` y las figuras en `docs/figuras/`.

## Pruebas

Las pruebas de integración usan un proveedor de modelos simulado y no requieren Ollama:

```bash
pytest -q
```

## Configuración

Todos los parámetros están en `config.yaml`: modelos por ruta, embedding, fragmentación, k y umbral de
recuperación, umbral de la caché semántica y del ciclo de agente. Los valores marcados como *calibrado* los
ajusta la evaluación.

## Nota ética

Las respuestas son generadas por modelos de lenguaje y pueden contener errores; cada hallazgo debe
verificarse contra el control citado. El corpus proviene de fuentes de dominio público (ver
`corpus/LICENCIAS.md`). En la elaboración de este proyecto se usó un asistente de IA para generar y
documentar código y para redactar borradores; las decisiones de arquitectura, la revisión y las pruebas son
responsabilidad de la autora (ver el informe técnico, sección de ética).
