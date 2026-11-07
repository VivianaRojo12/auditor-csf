# Levanta el sistema para la demostración (Windows, sin Claude Code).
#   powershell -ExecutionPolicy Bypass -File iniciar.ps1
# Abre el servicio (API, puerto 8000) y la aplicación web (puerto 8080) en dos ventanas y abre el navegador.

$ErrorActionPreference = "Stop"
$raiz = $PSScriptRoot
Set-Location $raiz
$pyv = Join-Path $raiz ".venv\Scripts\python.exe"
if (-not (Test-Path $pyv)) { Write-Host "Primero corre configurar.ps1" -ForegroundColor Red; exit 1 }

# Verificar que el corpus esté indexado; si no, indexarlo
Write-Host "Verificando el índice del corpus..." -ForegroundColor Yellow
& $pyv -c "from servicio.contenedor import Contenedor; c=Contenedor(); import sys; sys.exit(0 if c.base.contar()>0 else 1)" 2>$null
if ($LASTEXITCODE -ne 0) {
  Write-Host "Indexando el corpus..." -ForegroundColor Yellow
  & $pyv -m scripts.ingestar_corpus
}

Write-Host "Levantando el servicio (puerto 8000) y la web (puerto 8080)..." -ForegroundColor Green
Start-Process -FilePath $pyv -ArgumentList "-m", "servicio.main" -WorkingDirectory $raiz
Start-Sleep -Seconds 6
Start-Process -FilePath $pyv -ArgumentList "web/servidor_web.py", "8080", "http://127.0.0.1:8000" -WorkingDirectory $raiz
Start-Sleep -Seconds 3
Start-Process "http://127.0.0.1:8080"
Write-Host ""
Write-Host "Sistema arriba:" -ForegroundColor Cyan
Write-Host "  Aplicacion web: http://127.0.0.1:8080" -ForegroundColor White
Write-Host "  API / OpenAPI:  http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host "Para detener, cierra las dos ventanas de Python que se abrieron." -ForegroundColor Cyan
