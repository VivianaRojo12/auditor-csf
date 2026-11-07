# ADR-05: Fragmentación del corpus

- **Estado:** Aceptada
- **Atributo de calidad en juego:** calidad de la recuperación y tamaño del contexto.

## Contexto
Cada control del SP 800-53 tiene enunciado y guía, con longitudes muy distintas. Fragmentos muy grandes
diluyen la señal del embedding; muy pequeños parten el enunciado de su guía.

## Decisión
Fragmentación por tamaño con solapamiento (800 caracteres, 120 de solapamiento por defecto, calibrado),
cortando en límites de línea o palabra y conservando en los metadatos el control, la familia y la función
CSF. La recuperación usa k y umbral calibrados; los fragmentos bajo el umbral se descartan.

## Alternativas
- Un fragmento por control completo: algunos controles exceden la ventana y mezclan subtemas.
- Fragmentación por oración: pierde el contexto del control.

## Evidencia
Experimento de embeddings (acierto@k) en `embeddings.json`; parámetros k/umbral en `config.yaml`.

## Consecuencias
Recuperación con buena precisión manteniendo los metadatos de cada control. A cambio, el solapamiento
aumenta ligeramente el número de fragmentos (alrededor de 900 para ~300 controles).
