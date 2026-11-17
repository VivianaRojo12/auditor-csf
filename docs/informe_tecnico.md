---
titulo: "Auditor de políticas de seguridad contra NIST CSF 2.0"
subtitulo: "Producto inteligente en capas con modelos de lenguaje, embeddings y RAG"
---

# Auditor de políticas de seguridad contra NIST CSF 2.0

## Control de versiones

| Versión | Fecha | Cambios en el sistema | Cambios en este informe |
|---|---|---|---|
| 1.0 | 07-nov-2026 | Primera versión completa: servicio en capas (C1 a C7, T1 y T2), API REST, aplicación web, ingesta del corpus de 301 controles, seis ADR, diez diagramas y pruebas con un proveedor simulado. | Primera redacción: idea, arquitectura, comportamiento, selección de modelos y diseño por capa. |
| 1.1 | 07-nov-2026 | Evaluación completa y calibración de `config.yaml`; la ruta compleja pasa de `qwen2.5:7b` a `llama3.2:3b`. Reevaluación de la fidelidad con un procedimiento corregido: ambas respuestas (con y sin RAG) se califican contra los mismos controles, el juez (`qwen2.5:7b`) recibe el contexto completo y se agrega la métrica de citas válidas, que no depende del juez. | Se llenan las tablas de resultados (secciones 7 y 10) y se agregan las figuras 11 a 14. |
| 1.2 | 13-nov-2026 | Limpieza de la configuración y de los nombres heredados del prototipo anterior: variables de entorno `AUDITOR_*`, colección `controles_80053`, bitácora `auditor.jsonl` y retiro de dos guardrails que no aplicaban al dominio. | Sin cambios de fondo. |
| 1.3 | 14-nov-2026 | ADR-07: las fuentes se etiquetan con su control y la salida solo puede citar controles recuperados; nuevo campo `requisito` en cada hallazgo. Las citas válidas con RAG suben de 32.4 % a 100 % y la fidelidad de 1.33 a 2.09. Ejemplos de demostración en Markdown, PDF y DOCX. | Se describe el ADR-07 (secciones 8 y 9); el registro pasa de seis a siete ADR y se regenera la figura 13. |
| 1.4 | 16-nov-2026 | Avance de la auditoría sección por sección (`POST /auditorias/stream`) con cancelación; las rutas de auditoría ya no bloquean el servidor; en la web, carga por arrastre, selector de ejemplos y estado del servicio con el componente que falta. | Sin cambios de fondo. |
| 1.5 | 17-nov-2026 | Nueva interfaz web: barra lateral que separa lo del usuario de lo del sistema, informe con filtros y exportación, catálogo de controles, cuestionarios de práctica con datos oficiales, resultados de práctica anónimos en las métricas, recuadro de progreso que permite navegar mientras se audita e ilustraciones de gatos como guía visual. | Se agregan este control de versiones, la sección 5.1 (capa de presentación), las funciones de catálogo y práctica en los requisitos y en el diseño por capa, las citas válidas en la tabla de resultados, el trabajo futuro y la declaración de las imágenes. |

## 1. Resumen

Este informe describe el diseño y la construcción de un producto inteligente que audita políticas y
procedimientos de seguridad de la información contra los controles del **NIST SP 800-53 Rev. 5** y presenta
los hallazgos organizados por las seis funciones del **NIST CSF 2.0**. El producto recibe un documento y
entrega un informe de brechas con el estado de cada control, su gravedad, la evidencia citada y una
redacción corregida; no es un chatbot. El servicio implementa una arquitectura en capas con las capas
obligatorias de una aplicación de IA en producción —construcción de contexto con RAG, guardrails,
enrutador y gateway de modelos, caché, orquestación con ciclo de agente, observabilidad y
retroalimentación— y se expone como una API REST consumida por una aplicación web. La web muestra el avance
de cada auditoría mientras el usuario navega y suma un catálogo de controles y cuestionarios de práctica que
usan solo datos oficiales del corpus. Todo se ejecuta de forma local sobre modelos servidos con Ollama.

## 2. La idea del producto (ficha)

| Elemento | Descripción |
|---|---|
| Nombre del producto | Auditor de políticas de seguridad contra NIST CSF 2.0 |
| Usuario y contexto de uso | Responsable de seguridad de la información de una organización de infraestructura crítica, al revisar si sus políticas y procedimientos cubren un marco de control reconocido |
| Problema que resuelve | Comparar un documento interno contra cientos de controles es lento y propenso a omisiones; exige experiencia y tiempo |
| Resultado que entrega | Un informe de brechas por función del CSF 2.0: por cada control relevante, su estado (cubierto / parcial / ausente), gravedad, evidencia textual, control citado y redacción corregida. No es una conversación |
| Tipo de producto | Combinación de auditor de documentos, clasificador/priorizador y generador fundamentado |
| Cómo intervienen modelos, embeddings y RAG | Los embeddings indexan el catálogo de controles; el RAG recupera, por sección, los controles pertinentes; el modelo determina cobertura, gravedad y redacción corregida citando la fuente recuperada |
| Qué lo hace original | Cambia el resultado (de responder a emitir un informe estructurado accionable) y combina tres tipos de producto; aplica a un problema local y real de cumplimiento |
| Cómo se medirá su valor | Acierto@k de la recuperación, fidelidad al contexto con y sin RAG, porcentaje de brechas correctamente identificadas sobre un conjunto de prueba, y reducción de tiempo frente a la revisión manual |

La función principal entrega un artefacto (el informe) dentro del flujo de trabajo del usuario; la
conversación sobre los controles es una función secundaria (endpoint `/preguntas`). Como apoyo, el producto
incluye un catálogo de los 301 controles con su texto oficial y cuestionarios de práctica para estudiarlos;
ninguno de los dos usa un modelo de lenguaje, de modo que la respuesta correcta siempre es un dato del corpus.

## 3. Dominio del problema y corpus

El dominio es el cumplimiento de controles de seguridad en infraestructura crítica. La base de conocimiento
es el catálogo **NIST SP 800-53 Rev. 5**, obtenido en formato OSCAL del repositorio oficial
`usnistgov/oscal-content`. Es de dominio público (obra del gobierno de EE. UU., con dedicación CC0 1.0). El
script `scripts/construir_corpus_80053.py` extrae el enunciado y la guía de cada control base —se omiten las
mejoras de control para mantener el corpus enfocado— y genera un documento Markdown por control, con la
familia y la función del CSF 2.0 asociada. El corpus resultante es de **301 controles** (≈1.3 MB), lo que
supera el mínimo sugerido de 20 documentos o 50 páginas. Los documentos que se auditan en la demostración y
en la evaluación son políticas ficticias creadas para el proyecto, sin datos personales reales (ver
`corpus/LICENCIAS.md`).

El corpus está en inglés y los documentos a auditar en español, por lo que el modelo de embeddings debe ser
multilingüe; esto se aborda en la selección de modelos (sección 7) y en el ADR-01.

## 4. Requisitos y atributos de calidad

**Requisitos funcionales:** cargar un documento (PDF, DOCX, Markdown o texto); auditar por secciones contra
el corpus; emitir un informe con estado, gravedad, evidencia, control citado y recomendación; agrupar por
función del CSF; mostrar el avance de la auditoría y permitir cancelarla; exportar el informe (PDF, CSV y
JSON); registrar retroalimentación; exponer métricas; responder consultas puntuales con fuentes; consultar el
catálogo de controles; practicar con cuestionarios y registrar sus resultados de forma anónima.

**Atributos de calidad priorizados y medibles:**

| Atributo | Métrica | Meta orientativa |
|---|---|---|
| Exactitud de recuperación | acierto@3 (nivel familia de control) | ≥ 0.80 |
| Fidelidad al contexto | puntaje de juez 0–5, con y sin RAG | con RAG ≥ 4, y > sin RAG |
| Privacidad | datos personales en claro enviados o devueltos | 0 |
| Seguridad | bloqueos correctos de inyección | 100 % de las entradas problemáticas |
| Latencia | tiempo por consulta en el equipo local | < 2 min por sección (ruta compleja) |
| Uso de recursos | RAM del modelo activo | dentro de 32 GB |

Los valores medidos se reportan en la sección 10.

## 5. Arquitectura

El sistema tiene dos contenedores: la aplicación web (capa de presentación) y el servicio (lógica de
negocio). Dentro del servicio, el código se organiza en capas; cada capa solo usa a las de abajo por
interfaces, y las dos capas transversales (observabilidad y retroalimentación) pueden ser usadas por todas.
La elección de los adaptadores concretos (Ollama o simulado, Chroma o memoria) ocurre en un único lugar, la
raíz de composición (`servicio/contenedor.py`), de modo que las capas superiores dependen solo de
interfaces (`servicio/datos/interfaces.py`).

**Figura 1. Diagrama de contexto.**

![Diagrama de contexto](figuras/01_contexto.png)

**Figura 2. Diagrama de contenedores.**

![Diagrama de contenedores](figuras/02_contenedores.png)

**Figura 3. Capas del servicio y dirección de dependencias.**

![Capas del servicio](figuras/03_capas.png)

**Figura 4. Componentes principales por capa.**

![Componentes](figuras/04_componentes.png)

**Figura 5. Despliegue local.**

![Despliegue local](figuras/05_despliegue.png)

Responsabilidad e interfaz de cada capa:

| Capa | Responsabilidad | Interfaz principal |
|---|---|---|
| C1 Interfaz del servicio | Recibe HTTP, valida entrada/salida, traduce a llamadas de orquestación; sin lógica de IA | `servicio/api/app.py` (FastAPI) |
| C2 Orquestación y agente | Coordina el flujo de cada consulta; implementa el ciclo de agente | `Orquestador.analizar_seccion` |
| C3 Guardrails | Verificaciones de entrada y salida con política por falla | `verificar_entrada`, `verificar_salida` |
| C4 Caché | Caché exacta y semántica con invalidación y expiración | `CacheConsultas.buscar/guardar` |
| C5 Construcción de contexto | Lectura y fragmentación, RAG, armado del prompt | `ConstructorContexto` |
| C6 Enrutador y gateway | Clasifica la consulta y ofrece interfaz única a los modelos con tiempo límite y respaldo | `Enrutador`, `GatewayModelos` |
| C7 Acceso a datos y modelos | Adaptadores a Ollama, base vectorial y SQLite | interfaces en `datos/interfaces.py` |
| T1 Observabilidad | Traza por consulta, bitácoras por capa, métricas | `observador` |
| T2 Retroalimentación | Opinión del usuario ligada a la traza | `ServicioRetroalimentacion` |

### 5.1 Capa de presentación

La aplicación web (`web/`) es una sola página que consume únicamente la API por HTTP. Una barra lateral
separa lo que usa quien audita (Auditar, Último informe, Catálogo de controles, Practicar y Preguntar) de lo
que muestra cómo funciona el sistema (Métricas y configuración, y Créditos). Las secciones cambian sin
recargar la página, por lo que una auditoría sigue corriendo mientras el usuario navega.

- **Avance en vivo.** La web usa `POST /auditorias/stream`, que envía en NDJSON un evento al empezar y al
  terminar cada sección, y el informe completo al final. Un recuadro en la barra lateral muestra solo el
  progreso; los detalles técnicos de la sección (ruta, modelo, caché, guardrails, iteraciones del agente y
  traza) se ven aparte, en un bloque plegable. Si el usuario cierra la conexión, el servicio se detiene al
  terminar la sección en curso.
- **Informe.** Indicadores, cobertura de las seis funciones (las que no se tocaron aparecen como "Sin
  evaluar"), hallazgos con filtros por estado, gravedad y función, y exportación a PDF, CSV y JSON.
- **Catálogo y práctica.** `GET /controles` y `GET /controles/{id}` sirven el texto oficial de cada control;
  `GET /cuestionarios` arma preguntas de opción múltiple con el identificador, el nombre, la familia y el
  texto de los controles. Las preguntas nunca usan la función del CSF, porque esa correspondencia es de
  trabajo y no oficial. El progreso de cada persona se guarda en su navegador y el resultado de cada
  cuestionario se envía de forma anónima (`POST /cuestionarios/resultados`) para las métricas.
- **Accesibilidad y funcionamiento local.** Controles nativos navegables con teclado, estados que no dependen
  solo del color, diseño que se adapta a teléfono y tipografía incluida en el sitio para funcionar sin
  internet. Las ilustraciones de gatos acompañan los estados (trabajando, listo, error, puntaje) y su origen
  se declara en la sección 12.

## 6. Comportamiento

El flujo de una consulta sigue los pasos de la sección 4.2 del enunciado. Se documentan cinco escenarios.

**Figura 6. Secuencia: ingesta de un documento.**

![Secuencia de ingesta](figuras/06_secuencia_ingesta.png)

**Figura 7. Secuencia: consulta normal (recorrido completo por las capas).**

![Secuencia de consulta normal](figuras/07_secuencia_consulta.png)

**Figura 8. Secuencia: respuesta desde la caché semántica.**

![Secuencia desde caché](figuras/08_secuencia_cache.png)

**Figura 9. Secuencia: consulta bloqueada por los guardrails.**

![Secuencia bloqueada](figuras/09_secuencia_bloqueada.png)

**Figura 10. Secuencia: ciclo de agente ante recuperación pobre.**

![Secuencia del ciclo de agente](figuras/10_secuencia_agente.png)

## 7. Selección de modelos y enrutamiento

Se compararon al menos dos modelos de lenguaje y dos de embeddings sobre el mismo corpus y las mismas
preguntas de prueba (`evaluacion/experimento_embeddings.py` y `experimento_modelos.py`). El experimento de
embeddings mide acierto@k a nivel familia de control sobre 22 casos de prueba; el de modelos mide latencia,
tokens de salida, validez del esquema JSON y fidelidad según un modelo juez, sobre el mismo contexto
recuperado.

**Modelos de embeddings comparados:** `nomic-embed-text`, `bge-m3` y `mxbai-embed-large`.
**Modelos de lenguaje comparados:** `qwen2.5:3b`, `llama3.2:3b` y `qwen2.5:7b`.

Resultados del experimento (se completan con la corrida local):

> `[[TABLA_EMBEDDINGS]]`

**Figura 11. Recuperación por modelo de embeddings.**

![Acierto por embedding](figuras/embeddings_acierto.png)

> `[[TABLA_MODELOS]]`

**Figura 12. Modelos de lenguaje: latencia frente a fidelidad.**

![Latencia vs fidelidad](figuras/modelos_latencia_fidelidad.png)

**Criterio del enrutador.** El resultado alimenta directamente al enrutador (C6): el modelo pequeño y
rápido atiende la ruta simple y el más capaz la ruta compleja. La sección se clasifica por un criterio
explícito y barato (temas de control presentes y longitud), sin llamar a un modelo (ADR-02). La conclusión
sobre qué modelo se usa en cada ruta, qué se sacrifica y por qué el compromiso es adecuado para el equipo
disponible se deriva de las tablas anteriores y queda registrada, ya calibrada, en `config.yaml`.

## 8. Diseño de cada capa

**C5 Construcción de contexto (RAG).** Ingesta de varios formatos (PDF, DOCX, Markdown, texto). El documento
se divide en secciones por encabezados para auditarlo sección por sección, y el corpus se fragmenta por
tamaño con solapamiento conservando metadatos de control, familia y función (ADR-05). La recuperación usa
similitud coseno con k y umbral calibrados; los fragmentos bajo el umbral se descartan. El prompt limita la
respuesta al contexto y agrupa los fragmentos por control, de modo que cada fuente se identifica con el
control al que pertenece (por ejemplo, [IA-2]). La salida estructurada restringe el campo control_id a los
controles recuperados y exige copiar el requisito del control que sustenta cada hallazgo (ADR-07). La misma
capa lee el corpus para el catálogo y arma los cuestionarios (`servicio/contexto/catalogo.py`): las opciones
incorrectas se toman de la misma familia y se descartan los requisitos repetidos entre controles, para que
cada pregunta tenga una sola respuesta correcta.

**C3 Guardrails.** Tres verificaciones de entrada (documento válido, inyección de instrucciones, datos
personales) y tres de salida (esquema válido, fuentes válidas/apego al contexto, sin datos personales), cada
una con su política ante la falla (bloquear, anonimizar, reintentar o descartar). Detalle en ADR-04.

**C4 Caché.** Caché exacta por hash y semántica por similitud de embeddings, con umbral alto para no servir
respuestas de otra sección, TTL e invalidación al cambiar el corpus; la llave incluye una huella de la
configuración (ADR-03).

**C6 Enrutador y gateway.** El gateway ofrece una interfaz única a todos los modelos con tiempo límite,
reintentos, modelo de respaldo y registro de uso por llamada. El enrutador decide la ruta (ADR-02).

**C2 Orquestación y ciclo de agente.** Coordina el flujo y, ante recuperación pobre, reformula la consulta y
vuelve a buscar hasta un máximo de iteraciones (ADR-06).

**T1 Observabilidad.** Identificador de traza por consulta, bitácoras JSON por capa y métricas (latencia por
capa, aciertos de caché, activaciones de guardrails, modelo elegido, iteraciones de agente). Endpoint
`/metricas` y `/trazas/{id}`. Los resultados de práctica se registran como eventos de esta capa, sin datos
de la persona, y las métricas muestran las familias con menor tasa de aciertos.

**T2 Retroalimentación.** El usuario califica cada informe (útil / no útil y comentario); la
retroalimentación se liga a la traza y se incluye en el análisis de la evaluación.

## 9. Registro de decisiones de arquitectura (ADR)

Se registran siete ADR (carpeta `docs/adr/`): selección de modelos (ADR-01), criterio del enrutador
(ADR-02), umbral de la caché semántica (ADR-03), verificaciones de los guardrails (ADR-04), fragmentación
(ADR-05), diseño del ciclo de agente (ADR-06) y fuentes etiquetadas por control (ADR-07). Cada uno sigue la plantilla de contexto, decisión,
alternativas, evidencia y consecuencias, y se apoya en un atributo de calidad.

## 10. Evaluación y análisis de resultados

Los conjuntos de prueba están en `evaluacion/datos/`: 22 casos de recuperación con su control esperado, 11
entradas problemáticas y 10 normales para los guardrails, y 10 secciones etiquetadas para el enrutador. La
evaluación se ejecuta con `python -m evaluacion.ejecutar_todo` y escribe `evaluacion/resultados/`.

Resultados (se completan con la corrida local):

> `[[TABLA_SISTEMA]]`

**Figura 13. Impacto del RAG en la fidelidad.**

![Impacto del RAG](figuras/rag_impacto.png)

**Figura 14. Latencia promedio por capa.**

![Latencia por capa](figuras/latencia_por_capa.png)

**Análisis de errores.** `[[ANALISIS]]` (se redacta a partir de los casos fallidos del detalle en
`sistema.json`: p. ej., controles con familias cercanas confundidas, o secciones vagas que requieren el
ciclo de agente).

## 11. Limitaciones, riesgos y trabajo futuro

- **Alucinaciones.** El modelo podría proponer una redacción corregida imprecisa; se mitiga anclando cada
  hallazgo a una fuente recuperada (guardrail de fuentes válidas) y mostrando el control citado, pero el
  usuario debe verificar.
- **Corpus en inglés.** La recuperación es translingüe; aunque `bge-m3` la soporta bien, puede perder matices
  frente a un corpus en español. Trabajo futuro: incorporar una traducción o un marco en español.
- **Correspondencia CSF–800-53.** La tabla familia → función es de trabajo, no un crosswalk oficial de NIST;
  sirve para agrupar, no para certificar cumplimiento.
- **Sesgos y cobertura.** El catálogo no agota los controles posibles; un "cubierto" significa alineación con
  el control citado, no cumplimiento integral.
- **Privacidad y seguridad.** Los guardrails anonimizan datos personales y bloquean inyección; aun así, el
  corpus de entrada no debe contener datos sensibles reales sin anonimizar.
- **Fidelidad por debajo de la meta.** La fidelidad con RAG (2.09) mejoró con el ADR-07, pero sigue por
  debajo de la meta de 4; es una limitación del modelo de 3B en el equipo disponible.
- **Trabajo futuro.** Guardar las auditorías en el servidor para tener un historial y comparar versiones de
  una política (hoy la web conserva solo el último informe, en el navegador); llevar el progreso de práctica
  al servidor para que siga a la persona entre equipos.

## 12. Referencias y anexos

- National Institute of Standards and Technology. *SP 800-53 Rev. 5, Security and Privacy Controls for
  Information Systems and Organizations.* Catálogo OSCAL, repositorio `usnistgov/oscal-content` (dominio
  público, CC0 1.0).
- National Institute of Standards and Technology. *The NIST Cybersecurity Framework (CSF) 2.0*, 2024.
- Anexos: `README.md` (instalación y ejecución) y documentación OpenAPI del servicio (`/docs`).

### Uso de asistentes de IA

En la elaboración del proyecto se usó un asistente de IA para generar y documentar el código y para redactar
borradores de este informe. Las decisiones de arquitectura, la revisión del código, la ejecución de los
experimentos y el análisis de los resultados son responsabilidad de la autora.

### Imágenes de la interfaz

El logo y las ilustraciones de gatos que acompañan el progreso y los cuestionarios se obtuvieron de
internet, son de autoría no identificada y no son obra de la autora. Se usan solo con fines académicos y no
comerciales; se les eliminó el fondo con la herramienta de código abierto rembg. El detalle de origen,
procesamiento y uso de cada imagen está en `web/img/CREDITOS.md`.
