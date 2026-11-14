# Cómo ejecutar el proyecto (Windows)

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

## Presentación

Las diapositivas están en `docs\presentacion.html` (se navegan con las flechas).

## Obtener el código

```
git clone https://github.com/VivianaRojo12/auditor-csf.git
cd auditor-csf
```
