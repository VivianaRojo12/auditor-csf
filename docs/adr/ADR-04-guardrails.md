# ADR-04: Verificaciones de los guardrails

- **Estado:** Aceptada
- **Atributo de calidad en juego:** seguridad, privacidad y apego al contexto.

## Contexto
El documento auditado es texto no confiable: puede contener intentos de inyección de instrucciones y datos
personales (CURP, RFC, correos, teléfonos). La salida del modelo puede inventar controles o filtrar datos
personales.

## Decisión
Tres verificaciones de entrada (documento válido → bloquear; inyección de instrucciones → bloquear; datos
personales → anonimizar y continuar) y tres de salida (esquema válido → reintentar; fuentes válidas →
descartar hallazgos sin fuente recuperada; sin datos personales → anonimizar). Cada falla tiene una
política explícita.

## Alternativas
- Solo validación de esquema: no protege contra inyección ni privacidad.
- Anonimizar con un modelo: más costoso y menos predecible que los patrones.

## Evidencia
`evaluacion/datos/guardrails.json` (11 entradas problemáticas + 10 normales); `sistema.json`: porcentaje de
bloqueos correctos y de falsos positivos.

## Consecuencias
El sistema bloquea inyecciones y nunca envía ni devuelve datos personales en claro, y cada hallazgo queda
anclado a una fuente real. A cambio, los patrones pueden generar algún falso positivo, que se mide y acota.
