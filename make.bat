@echo off
setlocal enabledelayedexpansion

set PYTHON_BIN=python
set RUFF_BIN=ruff
set MYPY_BIN=mypy
set PYTEST_BIN=pytest

if exist ".venv\Scripts\python.exe" set PYTHON_BIN=.venv\Scripts\python.exe
if exist ".venv\Scripts\ruff.exe" set RUFF_BIN=.venv\Scripts\ruff.exe
if exist ".venv\Scripts\mypy.exe" set MYPY_BIN=.venv\Scripts\mypy.exe
if exist ".venv\Scripts\pytest.exe" set PYTEST_BIN=.venv\Scripts\pytest.exe

set TARGET=%1
if "%TARGET%"=="" set TARGET=check

if /i "%TARGET%"=="setup" goto target_setup
if /i "%TARGET%"=="backend-dev" goto target_backend_dev
if /i "%TARGET%"=="frontend-dev" goto target_frontend_dev
if /i "%TARGET%"=="migrate" goto target_migrate
if /i "%TARGET%"=="test" goto target_test
if /i "%TARGET%"=="lint" goto target_lint
if /i "%TARGET%"=="typecheck" goto target_typecheck
if /i "%TARGET%"=="frontend-test" goto target_frontend_test
if /i "%TARGET%"=="build" goto target_build
if /i "%TARGET%"=="check" goto target_check

echo Unknown target: %TARGET%
echo Available targets: setup, backend-dev, frontend-dev, migrate, test, lint, typecheck, frontend-test, build, check
exit /b 1

:target_setup
%PYTHON_BIN% -m pip install -r requirements\dev.txt || exit /b 1
cd frontend && call npm install && cd .. || exit /b 1
exit /b 0

:target_backend_dev
%PYTHON_BIN% manage.py runserver 0.0.0.0:8000
exit /b 0

:target_frontend_dev
cd frontend && call npm run dev
exit /b 0

:target_migrate
%PYTHON_BIN% manage.py migrate || exit /b 1
exit /b 0

:target_test
%PYTEST_BIN% || exit /b 1
exit /b 0

:target_lint
%RUFF_BIN% check . || exit /b 1
cd frontend && call npm run lint && cd .. || exit /b 1
exit /b 0

:target_typecheck
%MYPY_BIN% . || exit /b 1
cd frontend && call npm run typecheck && cd .. || exit /b 1
exit /b 0

:target_frontend_test
cd frontend && call npm test && cd .. || exit /b 1
exit /b 0

:target_build
cd frontend && call npm run build && cd .. || exit /b 1
exit /b 0

:target_check
echo === [1/6] Running Linting ===
%RUFF_BIN% check . || exit /b 1
cd frontend && call npm run lint && cd .. || exit /b 1

echo === [2/6] Running Typechecks ===
%MYPY_BIN% . || exit /b 1
cd frontend && call npm run typecheck && cd .. || exit /b 1

echo === [3/6] Running Backend Tests ===
%PYTEST_BIN% || exit /b 1

echo === [4/6] Running Frontend Tests ===
cd frontend && call npm test && cd .. || exit /b 1

echo === [5/6] Building Frontend Bundle ===
cd frontend && call npm run build && cd .. || exit /b 1

echo === [6/6] Django System Check ===
%PYTHON_BIN% manage.py check || exit /b 1

echo === ALL CHECKS PASSED ===
exit /b 0
