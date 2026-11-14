# ADR-07: Fuentes etiquetadas por control y salida restringida a controles recuperados

- **Estado:** Aceptada
- **Atributo de calidad en juego:** fidelidad (cada hallazgo debe sustentarse en un control recuperado).

## Contexto
En la evaluación inicial solo el 32.4 % de las citas con RAG correspondía a un control recuperado y la
fidelidad con RAG fue 1.33 sobre 5. El diagnóstico mostró que las fuentes se etiquetaban por número de
fragmento (F1, F2...), así que el modelo devolvía "F1" como `control_id` o repetía el mismo control varias
veces con fragmentos distintos.

## Decisión
- Las fuentes se agrupan por control y se etiquetan con su identificador: `[IA-2] Nombre (función PR,
  similitud 0.72)`, con los fragmentos del mismo control unidos.
- El esquema de salida restringe `control_id` a un `enum` con los controles recuperados para esa sección.
- Cada hallazgo incluye el campo `requisito`, copiado del texto del control que lo sustenta.
- El guardrail de salida normaliza el identificador (por ejemplo "ac 2" a "AC-2") y descarta hallazgos cuyo
  control no fue recuperado.
- La versión de los prompts forma parte de la huella de configuración, para que la caché no devuelva
  respuestas generadas con el formato anterior.

## Alternativas
- Solo instrucciones en el prompt: el modelo de 3B no las respetaba de forma consistente.
- Validar después sin restringir el esquema: se descartarían muchos hallazgos y quedarían secciones vacías.

## Evidencia
`evaluacion/reevaluar_fidelidad.py` (22 casos, qwen2.5:3b y juez qwen2.5:7b): las citas válidas pasan de
32.4 % a 100 % y la fidelidad con RAG de 1.33 a 2.09; sin RAG se mantiene en 0.86. Resultados en
`evaluacion/resultados/fidelidad.json`.

## Consecuencias
El modelo ya no puede citar controles inexistentes ni ajenos al contexto recuperado. La fidelidad sigue por
debajo de la meta de 4: el modelo pequeño todavía interpreta mal algunos requisitos, de modo que los
hallazgos deben revisarse. Si la recuperación no trae el control correcto, el hallazgo no puede citarlo.
