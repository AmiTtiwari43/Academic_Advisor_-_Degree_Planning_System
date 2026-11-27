# Academic Advisor & Degree Planning Platform

**Project P02** — Multi-Institution Curriculum Rules Engine, Degree Planning Platform, and Faculty Advisor Workflow.

---

## 1. Overview

The Academic Advisor and Degree Planning Platform is a multi-tenant enterprise system designed for universities to:
1. Define complex, versioned academic curricula and prerequisite rule trees using PostgreSQL JSONB.
2. Evaluate student course eligibility via a sandboxed, deterministic, pure-Python prerequisite engine.
3. Conduct authoritative degree audits pinned to matriculation catalog editions.
4. Enable students to simulate multi-semester degree paths without mutating official transcripts.
5. Coordinate faculty advisor workflows, approvals, revisions, and authorized overrides backed by an append-only audit trail.

---

## 2. Locked Technology Stack

- **Backend:** Python 3.12, Django 5.x LTS, Django REST Framework, PostgreSQL 16, `psycopg` 3, `django-environ`, `django-cors-headers`, `django-filter`, `drf-spectacular`.
- **Backend Quality & Tooling:** `pytest`, `pytest-django`, `pytest-cov`, `factory-boy`, `ruff`, `mypy`, `django-stubs`.
- **Frontend:** Vite, React 18, TypeScript (`strict: true`), React Router, TanStack Query, `react-hook-form`, `zod`, Vitest, React Testing Library.
- **Visual Design:** Pure CSS Custom Properties and CSS Modules (design tokens matching `docs/design-system.md`). Self-hosted typography (`@fontsource/inter` and `@fontsource/source-serif-4`). Zero Tailwind, zero third-party component libraries.
- **Database:** PostgreSQL 16 with native JSONB indexing. Relational multi-tenancy scoped by institution.

---

## 3. Quick Start

### 3.1 Prerequisites
- Python 3.12+ (or active virtual environment)
- Node.js 20+ and npm
- Docker & Docker Compose (or local PostgreSQL 16 server)

### 3.2 Environment Setup
1. Copy the example environment configuration:
   ```bash
   cp .env.example .env
   ```

2. Start the development PostgreSQL 16 database:
   ```bash
   docker compose up -d
   ```

3. Install project dependencies:
   ```bash
   make setup
   # Or on Windows without GNU make:
   .\make.bat setup
   ```

4. Apply initial database migrations:
   ```bash
   make migrate
   # Or on Windows:
   .\make.bat migrate
   ```

5. Verify all checks and tests pass:
   ```bash
   make check
   # Or on Windows:
   .\make.bat check
   ```

### 3.3 Running Development Servers
- **Backend API (Django):**
  ```bash
  make backend-dev
  # Serves on http://127.0.0.1:8000/
  ```
- **Frontend SPA (Vite):**
  ```bash
  make frontend-dev
  # Serves on http://127.0.0.1:5173/ with automatic proxy to Django API
  ```

---

## 4. Make Targets & Quality Gate

Every phase enforces the quality gate via `make check`:

| Command | Purpose |
|---|---|
| `make setup` | Install Python dev dependencies and frontend NPM packages |
| `make migrate` | Apply database migrations to PostgreSQL |
| `make test` | Run backend test suite with Pytest |
| `make lint` | Run Ruff on Python code and ESLint on TypeScript code |
| `make typecheck` | Run Mypy on Python code and TSC on TypeScript code |
| `make frontend-test` | Run frontend component tests with Vitest |
| `make build` | Compile optimized production frontend bundle |
| `make check` | Run complete verification suite (lint, typecheck, test, frontend-test, build, django check) |

---

## 5. Architectural Documentation

- [Project & Feature Architecture Guide (No-Code Overview)](PROJECT_FEATURE_AND_ARCHITECTURE_GUIDE.md)
- [Build Plan & Phased Roadmap](docs/ANTIGRAVITY_BUILD_PLAN.md)
- [Architecture Specification](docs/architecture.md)
- [Visual Design System](docs/design-system.md)
- [Database Schema Specification](docs/database-schema.md)
- [API Contracts & Endpoints](docs/api-contracts.md)
- [Prerequisite Rule Grammar](docs/rule-grammar.md)
- [Security Threat Model](docs/threat-model.md)
- [Security Checklist & Permission Matrix](docs/security-checklist.md)
- [Implementation Status](docs/implementation-status.md)
- [Manual Feature Verification Guide](docs/MANUAL_FEATURE_VERIFICATION_GUIDE.md)
