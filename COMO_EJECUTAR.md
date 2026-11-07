# Cómo ejecutar el proyecto sin Claude Code (Windows)

Todo se hace con tres scripts. Ábrelos desde PowerShell, dentro de la carpeta del proyecto. Si PowerShell
bloquea la ejecución, usa el prefijo `powershell -ExecutionPolicy Bypass -File`.

## Antes de empezar

1. Instala [Python 3.11+](https://www.python.org/downloads/) (marca "Add python.exe to PATH").
2. Instala [Ollama](https://ollama.com) y déjalo abierto.
3. Descarga los modelos (una sola vez), en una terminal:
   ```
   ollama pull qwen2.5:7b
   ollama pull qwen2.5:3b
   ollama pull llama3.2:3b
   ollama pull nomic-embed-text
   ollama pull bge-m3
   ```

## Paso 1 — Configurar (unos minutos)

```
powershell -ExecutionPolicy Bypass -File configurar.ps1
```
Crea el entorno, instala dependencias, descarga el catálogo NIST, construye el corpus y corre las pruebas.

## Paso 2 — Evaluar (1 a 3 horas; deja la laptop conectada)

```
powershell -ExecutionPolicy Bypass -File evaluar.ps1
```
Compara los modelos, calibra la configuración, evalúa el sistema, genera las figuras y arma el informe con
los números reales en `docs\informe_tecnico.html`. Para el PDF: ábrelo e **Imprimir → Guardar como PDF**.

## Paso 3 — Levantar el sistema para la demostración

```
powershell -ExecutionPolicy Bypass -File iniciar.ps1
```
Abre el servicio (puerto 8000) y la web (puerto 8080) y lanza el navegador. Para detener, cierra las dos
ventanas de Python.

## Grabación del video

Con el sistema arriba, graba la pantalla siguiendo `docs\guion_video.md` y usa las diapositivas
`docs\presentacion.html` (se navegan con las flechas). Sube el video a Drive al final.

## Subir el repositorio a GitHub

**Opción A (más simple):** crea en github.com un repositorio **vacío** llamado `auditor-csf` (sin README).
Avísame el nombre y yo subo todo el proyecto por ti desde aquí.

**Opción B (desde tu laptop):** si tienes Git instalado y tu sesión de GitHub configurada:
```
git init
git add .
git commit -m "Auditor de políticas de seguridad contra NIST CSF 2.0"
git branch -M main
git remote add origin https://github.com/VivianaRojo12/auditor-csf.git
git push -u origin main
```
