# Evaluación completa con modelos reales (Windows, sin Claude Code).
#   powershell -ExecutionPolicy Bypass -File evaluar.ps1
# Compara modelos, calibra config.yaml, reindexa el corpus, evalúa el sistema, genera figuras y arma el
# informe. Tarda de 1 a 3 horas en CPU: deja la laptop conectada a la corriente y sin suspenderse.

$ErrorActionPreference = "Stop"
$raiz = $PSScriptRoot
Set-Location $raiz
$pyv = Join-Path $raiz ".venv\Scripts\python.exe"
if (-not (Test-Path $pyv)) { Write-Host "Primero corre configurar.ps1" -ForegroundColor Red; exit 1 }

# Verificar Ollama y los modelos
Write-Host "Verificando Ollama..." -ForegroundColor Yellow
try {
  $tags = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 5
  $instalados = $tags.models | ForEach-Object { $_.name; $_.name -replace ':latest$', '' }} catch {
  Write-Host "No se pudo conectar con Ollama en el puerto 11434. Abre la app de Ollama y vuelve a intentar." -ForegroundColor Red
  exit 1
}
$necesarios = @("qwen2.5:7b", "qwen2.5:3b", "llama3.2:3b", "nomic-embed-text", "bge-m3")
$faltan = $necesarios | Where-Object { $instalados -notcontains $_ }
if ($faltan.Count -gt 0) {
  Write-Host "Faltan modelos por descargar:" -ForegroundColor Red
  $faltan | ForEach-Object { Write-Host "  ollama pull $_" -ForegroundColor White }
  Write-Host "Descárgalos y vuelve a correr este script." -ForegroundColor Red
  exit 1
}
Write-Host "Modelos presentes. Iniciando la evaluación (esto tarda)..." -ForegroundColor Green

& $pyv -m evaluacion.ejecutar_todo

Write-Host ""
Write-Host "Evaluación terminada." -ForegroundColor Cyan
Write-Host "Informe: docs\informe_tecnico.html  (ábrelo e Imprimir -> Guardar como PDF)" -ForegroundColor White
Write-Host "Para la demostración, levanta el sistema con:" -ForegroundColor Cyan
Write-Host "  powershell -ExecutionPolicy Bypass -File iniciar.ps1" -ForegroundColor White
