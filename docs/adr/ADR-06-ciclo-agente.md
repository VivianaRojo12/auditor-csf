# ADR-06: Diseño del ciclo de agente

- **Estado:** Aceptada
- **Atributo de calidad en juego:** robustez de la recuperación frente a secciones mal redactadas o vagas.

## Contexto
Algunas secciones están redactadas de forma genérica ("cumplir con la normatividad vigente") y la
recuperación inicial es pobre: ningún control supera el umbral. Generar un análisis sobre un contexto pobre
produce hallazgos poco fundamentados.

## Decisión
Si la recuperación es pobre (mejor puntaje por debajo de un umbral), la orquestación entra en un ciclo de
agente: pide al modelo reformular la consulta en términos de objetivos de control y vuelve a buscar, hasta
un máximo de iteraciones. El ciclo tiene condición de salida (recuperación suficiente) y tope de
iteraciones para acotar la latencia.

## Alternativas
- No reformular: hallazgos pobres en secciones vagas.
- Reformular siempre: gasta una llamada extra incluso cuando la recuperación ya es buena.

## Evidencia
`evaluacion/evaluar_sistema.py` (eval_agente): porcentaje de consultas que mejoran tras reformular e
iteraciones promedio, en `sistema.json`.

## Consecuencias
Mejora la recuperación en secciones ambiguas sin afectar las claras. A cambio, esas secciones tardan más
por las iteraciones adicionales, acotadas por el máximo configurado.
