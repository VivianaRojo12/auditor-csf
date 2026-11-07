# ADR-02: Criterio del enrutador

- **Estado:** Aceptada
- **Atributo de calidad en juego:** latencia y costo de cómputo frente a calidad del análisis.

## Contexto
Cada sección de una política puede ser trivial (una definición, una firma) o abarcar varios dominios de
control. Usar siempre el modelo grande desperdicia tiempo en CPU; usar siempre el pequeño pierde calidad en
secciones complejas.

## Decisión
El enrutador clasifica cada sección con un criterio explícito y barato (sin llamar a un modelo): cuenta
señales de complejidad (temas de control presentes por patrones y longitud de la sección). Si el puntaje
alcanza un umbral, la sección va a la ruta compleja (modelo más capaz); si no, a la simple.

## Alternativas
- Clasificar con un modelo de lenguaje: más preciso pero añade una llamada y latencia a cada consulta.
- Enrutar por longitud únicamente: simple, pero una sección corta puede tocar varios dominios.
- Sin enrutador (un solo modelo): descartada en ADR-01.

## Evidencia
Conjunto `evaluacion/datos/enrutador.json` con secciones etiquetadas; resultado en `sistema.json`
(porcentaje de aciertos del enrutador).

## Consecuencias
Clasificación instantánea y transparente. A cambio, es heurística: puede equivocarse en secciones límite,
lo que se mitiga con un umbral calibrado y con el gateway que puede recurrir al modelo de respaldo.
