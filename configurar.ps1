# Configuración del proyecto en Windows, sin Claude Code.
# Ejecutar desde la carpeta del proyecto con:
#   powershell -ExecutionPolicy Bypass -File configurar.ps1
# Hace: entorno virtual, dependencias, descarga del catálogo NIST, construcción del corpus y pruebas.

$ErrorActionPreference = "Stop"
$raiz = $PSScriptRoot
Set-Location $raiz
Write-Host "== Auditor CSF: configuración ==" -ForegroundColor Cyan

# 1. Python y entorno virtual
$py = (Get-Command python -ErrorAction SilentlyContinue)
if (-not $py) { $py = (Get-Command py -ErrorAction SilentlyContinue) }
if (-not $py) { Write-Host "No se encontró Python. Instálalo desde python.org y vuelve a correr." -ForegroundColor Red; exit 1 }
if (-not (Test-Path ".venv")) {
  Write-Host "Creando entorno virtual..." -ForegroundColor Yellow
  & $py.Source -m venv .venv
}
$pyv = Join-Path $raiz ".venv\Scripts\python.exe"

# 2. Dependencias
Write-Host "Instalando dependencias..." -ForegroundColor Yellow
& $pyv -m pip install --upgrade pip --quiet
& $pyv -m pip install -r requisitos.txt --quiet
Write-Host "Dependencias instaladas." -ForegroundColor Green

# 3. Descargar el catálogo oficial NIST SP 800-53 Rev. 5 (dominio público)
$dirFuente = Join-Path $raiz "_corpus_fuente"
New-Item -ItemType Directory -Force -Path $dirFuente | Out-Null
$catalogo = Join-Path $dirFuente "NIST_SP-800-53_rev5_catalog.json"
if (-not (Test-Path $catalogo)) {
  $url = "https://raw.githubusercontent.com/usnistgov/oscal-content/main/nist.gov/SP800-53/rev5/json/NIST_SP-800-53_rev5_catalog.json"
  Write-Host "Descargando el catálogo NIST..." -ForegroundColor Yellow
  Invoke-WebRequest -Uri $url -OutFile $catalogo -UseBasicParsing
}
Write-Host "Catálogo listo." -ForegroundColor Green

# 4. Construir el corpus
Write-Host "Construyendo el corpus de controles..." -ForegroundColor Yellow
& $pyv scripts/construir_corpus_80053.py $catalogo corpus/controles

# 5. Pruebas (no requieren Ollama)
Write-Host "Ejecutando pruebas..." -ForegroundColor Yellow
& $pyv -m pytest -q
if ($LASTEXITCODE -ne 0) { Write-Host "Algunas pruebas fallaron; revisa el detalle arriba." -ForegroundColor Red }
else { Write-Host "Pruebas correctas." -ForegroundColor Green }

Write-Host ""
Write-Host "Configuración terminada." -ForegroundColor Cyan
Write-Host "Siguiente paso: descarga los modelos de Ollama (si no lo has hecho) y corre la evaluación:" -ForegroundColor Cyan
Write-Host "  powershell -ExecutionPolicy Bypass -File evaluar.ps1" -ForegroundColor White
