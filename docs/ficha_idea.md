# Ficha de la idea — Proyecto integrador

| Elemento | Respuesta |
|---|---|
| **Nombre del producto** | Auditor de políticas de seguridad contra NIST CSF 2.0 |
| **Usuario y contexto de uso** | Responsable de seguridad de la información de una organización de infraestructura crítica, cuando revisa si sus políticas y procedimientos cubren un marco de control reconocido antes de una auditoría o certificación. |
| **Problema que resuelve** | Comparar un documento interno contra cientos de controles de seguridad es lento, exige experiencia y se presta a omisiones. |
| **Resultado que entrega (no un chat)** | Un informe de brechas por función del NIST CSF 2.0. Por cada control relevante: estado (cubierto / parcial / ausente), gravedad, evidencia textual del documento, el control citado como fuente y una redacción corregida propuesta. |
| **Tipo de producto (del catálogo o combinación)** | Combinación de tres: auditor de documentos + clasificador/priorizador + generador fundamentado. |
| **Cómo intervienen los modelos, los embeddings y el RAG** | Los embeddings indexan el catálogo de controles NIST SP 800-53 Rev. 5 en una base vectorial. Para cada sección de la política, el RAG recupera los controles pertinentes; el modelo de lenguaje determina la cobertura, la gravedad y la redacción corregida, citando siempre la fuente recuperada. |
| **Qué lo hace original** | Cambia el resultado (de responder a emitir un informe estructurado accionable) y la entrada (recibe un documento, no una pregunta); combina tres tipos de producto; se aplica a un problema local y real de cumplimiento en infraestructura crítica. |
| **Cómo se medirá su valor** | Acierto@k de la recuperación, fidelidad al contexto con y sin RAG (modelo juez), porcentaje de brechas correctamente identificadas sobre un conjunto de prueba, y reducción de tiempo frente a la revisión manual. |

**Nota.** Todo corre de forma local (modelos servidos con Ollama, base vectorial, servicio y aplicación
web). El corpus proviene de fuentes de dominio público (NIST). La conversación sobre los controles existe
solo como función secundaria.
