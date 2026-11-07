# Mapa de entregables y rúbrica

Dónde está cada cosa que pide el proyecto.

## Entregables (sección 10 del enunciado)

| Entregable | Ubicación |
|---|---|
| Repositorio de código por capas | todo el proyecto; servicio en `servicio/`, web en `web/` |
| Informe técnico (PDF) | `docs/informe_tecnico.md` → se arma en `docs/informe_tecnico.html` y se imprime a PDF |
| Documentación de la API (OpenAPI) | generada por el servicio en `/docs` y `/openapi.json` |
| Conjuntos de prueba y resultados | `evaluacion/datos/` y `evaluacion/resultados/` |
| Presentación | `docs/presentacion.html` y guion en `docs/guion_video.md` |
| Ficha de la idea | `docs/ficha_idea.md` |

## Requisitos obligatorios (*)

| Requisito | Dónde se cumple |
|---|---|
| R1 Dominio y corpus propios | `corpus/controles` (301 controles), `corpus/LICENCIAS.md` |
| R2 Ejecución local | Ollama + Chroma + servicio + web, sin APIs en la nube |
| R3 Selección de modelos sustentada | `evaluacion/experimento_embeddings.py`, `experimento_modelos.py` |
| R4 Embeddings en base vectorial | `servicio/contexto/rag.py`, `servicio/datos/vectorial.py` |
| R5 RAG con fuentes | recuperación + prompts; cada hallazgo cita su control |
| R6 Arquitectura en capas | `servicio/` (C1–C7, T1, T2) |
| R7 Servicio con API REST | `servicio/api/app.py` (FastAPI, OpenAPI) |
| R8 Capa de presentación web | `web/` consume solo la API por HTTP |
| R9 Evaluación | `evaluacion/evaluar_sistema.py` |
| R10 Reproducibilidad | `README.md`, `requisitos.txt`, `PROMPT_MAESTRO.md` |
| R11 Informe técnico | `docs/informe_tecnico.md` |
| R12 Más allá de un chatbot | función principal = informe; chat solo secundario |

## Capas obligatorias (sección 4)

| Capa | Módulo |
|---|---|
| C1 API | `servicio/api/` |
| C2 Orquestación y agente | `servicio/orquestacion/` |
| C3 Guardrails | `servicio/guardrails/` |
| C4 Caché | `servicio/cache/` |
| C5 Construcción de contexto | `servicio/contexto/` |
| C6 Enrutador y gateway | `servicio/modelos/` |
| C7 Acceso a datos y modelos | `servicio/datos/` |
| T1 Observabilidad | `servicio/observabilidad/` |
| T2 Retroalimentación | `servicio/retroalimentacion/` |

## Diagramas (10) y ADR (6)

- Diagramas: `docs/diagramas/*.mmd` y `docs/figuras/01..10_*.png`.
- ADR: `docs/adr/ADR-01..06-*.md`.
