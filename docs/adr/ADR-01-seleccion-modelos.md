# ADR-01: Selección de modelos de lenguaje y de embeddings

- **Estado:** Aceptada
- **Atributo de calidad en juego:** exactitud de la recuperación y de los hallazgos, latencia, uso de recursos.

## Contexto
El sistema corre en una laptop con CPU integrada (sin GPU dedicada). Debe comparar la política contra un
corpus en inglés (SP 800-53) a partir de documentos en español, por lo que el modelo de embeddings necesita
ser multilingüe. Se requieren al menos dos modelos de lenguaje y dos de embeddings comparados con evidencia
(R3).

## Decisión
Se eligen el modelo de embeddings y los de lenguaje con base en el experimento de `evaluacion/` (acierto@k,
fidelidad, latencia y recursos). La configuración se calibra automáticamente: el embedding con mayor
acierto@3 y, para el enrutador, un modelo rápido para la ruta simple y uno más capaz para la compleja. Los
valores definitivos quedan en `config.yaml` tras `evaluacion/ejecutar_todo`.

## Alternativas
- Un solo modelo para todo: más simple, pero desperdicia latencia en consultas simples o sacrifica calidad
  en las complejas.
- Embeddings monolingües en inglés: peor recuperación translingüe sobre documentos en español.
- Modelos vía API en la nube: prohibido por R2 (ejecución local).

## Evidencia
`evaluacion/resultados/embeddings.json` y `modelos.json`; figuras `embeddings_acierto.png` y
`modelos_latencia_fidelidad.png`.

## Consecuencias
Mejor equilibrio entre calidad y latencia por tipo de consulta. A cambio, hay que mantener varios modelos
descargados y el enrutador añade una decisión por consulta.
