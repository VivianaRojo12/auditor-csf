# ADR-03: Umbral de similitud de la caché semántica

- **Estado:** Aceptada
- **Atributo de calidad en juego:** latencia frente a corrección (no servir una respuesta de otra sección).

## Contexto
La caché semántica evita reanalizar secciones parecidas comparando embeddings. Un umbral bajo serviría
respuestas incorrectas de secciones solo superficialmente parecidas; uno muy alto casi nunca acierta.

## Decisión
Se usa una caché de dos niveles: exacta por hash (misma sección y misma configuración) y semántica por
similitud coseno con umbral alto (0.95 por defecto, calibrado). La llave incluye una huella de la
configuración, de modo que un cambio de modelos o parámetros invalida la caché.

## Alternativas
- Solo caché exacta: no aprovecha secciones parafraseadas.
- Umbral bajo (p. ej. 0.85): más aciertos, pero riesgo de servir hallazgos de otra sección.

## Evidencia
`evaluacion/resultados/sistema.json`: tasa de aciertos exactos y semánticos, reducción de latencia y
respuestas incorrectas servidas desde la caché semántica.

## Consecuencias
Reducción fuerte de latencia en secciones repetidas o parecidas. A cambio, la caché semántica es
conservadora (pocos aciertos en parafraseo fuerte) para no sacrificar corrección.
