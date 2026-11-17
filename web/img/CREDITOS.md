# Imágenes de la interfaz

## Origen y uso

- **Logo** (`logo.png`) e **ilustraciones de gatos** (`michis/*.png`): imágenes obtenidas de internet, de
  autoría no identificada. No son obra de la autora del proyecto.
- `michi-piensa` y `michi-libro` provienen de publicaciones de la red social Xiaohongshu (traían su marca
  de agua); la marca se retiró al procesar la imagen, lo cual no cambia su autoría.
- **Uso:** exclusivamente académico y no comercial, como parte de un proyecto escolar sin publicación ni
  monetización. Si la persona titular de alguna imagen solicita su retiro, se reemplazará.

## Procesamiento

- **Logo:** recorte circular de la imagen original, en PNG con transparencia.
- **Ilustraciones:** se eliminó el fondo para mostrarlas en PNG transparente sobre los colores del sitio,
  con la herramienta de código abierto [rembg](https://github.com/danielgatis/rembg) (modelos
  `isnet-general-use`, `u2net` y `birefnet-general-lite`, ejecutados en local), más recortes y ajustes de
  borde. En `michi-piensa` y `michi-libro` se cubrió con blanco la marca de agua antes de eliminar el fondo.

## Uso de cada imagen en la interfaz

| Imagen | Momento |
|---|---|
| `michi-compu` | Auditoría en curso (recuadro de progreso) |
| `michi-lap` | Consulta en curso |
| `michi-libro` | Sección de práctica y progreso de estudio |
| `michi-ok` | Respuesta correcta, auditoría terminada, puntaje del 40 al 79 % |
| `michi-piensa` | Respuesta incorrecta, auditoría cancelada |
| `michi-festejo` | Puntaje del 80 al 100 % |
| `michi-tomatoso` | Error del sistema, puntaje del 0 al 39 % |
