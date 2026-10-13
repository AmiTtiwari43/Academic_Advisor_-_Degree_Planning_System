param(
    [Parameter(Position=0)]
    [string]$Target = "check"
)

$ErrorActionPreference = "Stop"

$PythonBin = "python"
$RuffBin = "ruff"
$MypyBin = "mypy"
$PytestBin = "pytest"

if (Test-Path ".venv\Scripts\python.exe") { $PythonBin = ".venv\Scripts\python.exe" }
if (Test-Path ".venv\Scripts\ruff.exe") { $RuffBin = ".venv\Scripts\ruff.exe" }
if (Test-Path ".venv\Scripts\mypy.exe") { $MypyBin = ".venv\Scripts\mypy.exe" }
if (Test-Path ".venv\Scripts\pytest.exe") { $PytestBin = ".venv\Scripts\pytest.exe" }

function Run-Step([string]$Name, [scriptblock]$Action) {
    Write-Host "=== $Name ===" -ForegroundColor Cyan
    & $Action
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Step failed: $Name"
        exit 1
    }
}

switch ($Target.ToLower()) {
    "setup" {
        Run-Step "Python Dev Dependencies" { & $PythonBin -m pip install -r requirements/dev.txt }
        Run-Step "Frontend NPM Dependencies" { Push-Location frontend; npm install; Pop-Location }
    }
    "backend-dev" {
        & $PythonBin manage.py runserver 0.0.0.0:8000
    }
    "frontend-dev" {
        Push-Location frontend; npm run dev; Pop-Location
    }
    "migrate" {
        Run-Step "Django Migrations" { & $PythonBin manage.py migrate }
    }
    "test" {
        Run-Step "Backend Pytest" { & $PytestBin }
    }
    "lint" {
        Run-Step "Backend Ruff Lint" { & $RuffBin check . }
        Run-Step "Frontend ESLint" { Push-Location frontend; npm run lint; Pop-Location }
    }
    "typecheck" {
        Run-Step "Backend Mypy" { & $MypyBin . }
        Run-Step "Frontend TSC" { Push-Location frontend; npm run typecheck; Pop-Location }
    }
    "frontend-test" {
        Run-Step "Frontend Vitest" { Push-Location frontend; npm test; Pop-Location }
    }
    "build" {
        Run-Step "Frontend Build" { Push-Location frontend; npm run build; Pop-Location }
    }
    "check" {
        Run-Step "Backend Ruff Lint" { & $RuffBin check . }
        Run-Step "Frontend ESLint" { Push-Location frontend; npm run lint; Pop-Location }
        Run-Step "Backend Mypy" { & $MypyBin . }
        Run-Step "Frontend TSC" { Push-Location frontend; npm run typecheck; Pop-Location }
        Run-Step "Backend Pytest" { & $PytestBin }
        Run-Step "Frontend Vitest" { Push-Location frontend; npm test; Pop-Location }
        Run-Step "Frontend Build" { Push-Location frontend; npm run build; Pop-Location }
        Run-Step "Django System Check" { & $PythonBin manage.py check }
        Write-Host "=== ALL CHECKS PASSED ===" -ForegroundColor Green
    }
    default {
        Write-Host "Unknown target: $Target" -ForegroundColor Red
        Write-Host "Available targets: setup, backend-dev, frontend-dev, migrate, test, lint, typecheck, frontend-test, build, check"
        exit 1
    }
}
