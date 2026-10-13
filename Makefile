.PHONY: help setup backend-dev frontend-dev migrate test lint typecheck frontend-test build check

help:
	@echo "Academic Advisor & Degree Planning System - Make Targets"
	@echo "  setup         - Install backend and frontend dependencies"
	@echo "  backend-dev   - Start Django development server"
	@echo "  frontend-dev  - Start Vite frontend dev server"
	@echo "  migrate       - Apply database migrations"
	@echo "  test          - Run backend test suite (pytest)"
	@echo "  lint          - Run backend and frontend linters"
	@echo "  typecheck     - Run backend and frontend type checkers"
	@echo "  frontend-test - Run frontend component tests (vitest)"
	@echo "  build         - Build production frontend bundle"
	@echo "  check         - Run complete verification gate"

setup:
	python -m pip install -r requirements/dev.txt
	cd frontend && npm install

backend-dev:
	python manage.py runserver 0.0.0.0:8000

frontend-dev:
	cd frontend && npm run dev

migrate:
	python manage.py migrate

test:
	pytest

lint:
	ruff check .
	cd frontend && npm run lint

typecheck:
	mypy .
	cd frontend && npm run typecheck

frontend-test:
	cd frontend && npm test

build:
	cd frontend && npm run build

check: lint typecheck test frontend-test build
	python manage.py check
