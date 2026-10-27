# Ultimate Production-Ready FastAPI Backend Starter Template

[![CI Quality Pipeline](https://github.com/example/fastapi-production-template/actions/workflows/ci.yml/badge.svg)](https://github.com/example/fastapi-production-template/actions)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%20%7C%203.13%20%7C%203.14-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2-e92063.svg)](https://docs.pydantic.dev/)
[![SQLAlchemy 2.x](https://img.shields.io/badge/SQLAlchemy-2.0+-red.svg)](https://www.sqlalchemy.org/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://img.shields.io/badge/mypy-strict-blue.svg)](https://mypy-lang.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An enterprise-grade, secure-by-default, fully typed, asynchronous backend starter repository architected for production deployments.

This repository is **not** a toy tutorial, a superficial CRUD demo, or a collection of disconnected snippets. It is a robust **Modular Monolith** foundation built following the design patterns used by Principal and Staff Engineers building real-world software.

---

## Key Highlights

- **Modern Asynchronous Stack**: Python 3.12+, FastAPI, Pydantic v2, `pydantic-settings`, SQLAlchemy 2.x async engine with `asyncpg` (PostgreSQL) and `aiosqlite` (zero-dependency local development/testing), Alembic migrations, Redis client, and HTTPX.
- **Explicit Transaction Management**: Clean separation of persistence and use cases. Repositories handle data mapping without hidden commits; Application Services own explicit transaction boundaries via `in_transaction`.
- **Advanced Security & Auth**: Argon2id password hashing (`argon2-cffi`), short-lived JWT access tokens with RFC 7519 `jti` tracking, rotatable refresh tokens persisted as SHA-256 hashes, and **automatic token family revocation upon breach/reuse detection**.
- **Role-Based Access Control (RBAC)**: Fine-grained permissions, ownership checks, and prevention of mass-assignment privilege escalation.
- **Centralized Error Handling**: Standardized machine-readable error contracts (`code`, `message`, `details`, `request_id`). No stack traces, raw SQL, or secret leaks in client responses.
- **Resilient API Infrastructure**: Distributed and in-memory rate limiting, idempotency handling via `Idempotency-Key` headers, request ID propagation, security defense-in-depth headers, and standardized offset and cursor pagination.
- **Enterprise Observability**: Correlated structured JSON logging with `structlog`, automatic credential redaction, OpenTelemetry hooks, and health probes (`/health/liveness`, `/health/readiness`).
- **Comprehensive Multi-Tier Test Suite**: Unit, integration, API, and security tests executing against isolated in-memory databases with 100% test pass rates.
- **Complete Developer Tooling**: Strict `ruff` linting and formatting, strict `mypy` static typing, multi-stage non-root `Dockerfile`, `compose.yaml`, `.pre-commit-config.yaml`, and `Makefile`.

---

## Architecture Overview

```
                      Client Request
                            ↓
               [Security & Context Middlewares]
         (Request ID, Logging, Security Headers, Idempotency)
                            ↓
                  [API Transport Routers]
              (Request Validation, RBAC Guards)
                            ↓
                [Application Service Layer]
              (Business Rules & Transaction Scope)
                            ↓
               [Domain Models & Repositories]
            (SQLAlchemy 2.x, Mixins, DB Constraints)
                            ↓
        [PostgreSQL / SQLite Database & Redis Cache]
```

### Directory Structure

```
├── app/
│   ├── api/                   # Routing, global dependencies, API versioning
│   │   ├── v1/                # Version 1 routing registry
│   │   │   └── endpoints/     # Cross-cutting endpoints (liveness & readiness)
│   ├── common/                # Shared domain primitives (enums, base schemas, utilities)
│   ├── core/                  # Platform infrastructure (config, logging, security, errors, middleware)
│   ├── db/                    # SQLAlchemy async engine, session lifecycle, transaction mixins
│   ├── infrastructure/        # External adapters (Redis, Cache, HTTP client, Outbox, Storage)
│   ├── modules/               # Feature-oriented domain modules
│   │   ├── auth/              # Authentication, tokens, rotation, breach detection
│   │   └── users/             # User domain, profiles, RBAC, administrative controls
│   ├── repositories/          # Generic BaseRepository abstraction and protocols
│   └── main.py                # FastAPI application factory and entry point
├── alembic/                   # Database migrations (async runner, autogenerate scripts)
├── docs/                      # Architectural documentation and ADRs
├── scripts/                   # Operational utilities (seed, migrate, test)
├── tests/                     # Multi-tier test suite (unit, integration, API, security)
├── Dockerfile                 # Multi-stage production container image
├── compose.yaml               # Docker Compose development environment
├── Makefile                   # Developer task automation
├── pyproject.toml             # Project dependencies and tool configurations
└── alembic.ini                # Alembic configuration
```

---

## Quickstart

### Prerequisites
- Python 3.12+ (Python 3.12, 3.13, or 3.14)
- Git
- Docker & Docker Compose (optional for local SQLite mode)

### 1. Clone & Set Up Virtual Environment

```bash
git clone https://github.com/example/fastapi-production-template.git
cd fastapi-production-template

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies with development tooling
make install
```

### 2. Configure Environment

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
*(The default `.env` is pre-configured with SQLite for instant zero-dependency local execution.)*

### 3. Run Database Migrations

```bash
make migrate
```

### 4. Seed Administrator Account (Optional)

```bash
make seed
```
Creates an initial administrator account:
- **Email**: `admin@example.com`
- **Password**: `AdminPassword123!`

### 5. Start Development Server

```bash
make dev
```
The server will start at `http://localhost:8000`.
Interactive OpenAPI documentation is available at `http://localhost:8000/docs`.

---

## Docker Compose Quickstart

To run the complete production-like environment with PostgreSQL 16 and Redis 7:

```bash
make docker-up
```

Stop the containers when finished:
```bash
make docker-down
```

---

## Developer Commands (`make`)

| Command | Description |
| :--- | :--- |
| `make install` | Install all dependencies and development tools |
| `make dev` | Start development server with auto-reload |
| `make check` | Run full quality suite: linting, typecheck, and tests |
| `make test` | Run complete automated test suite |
| `make test-unit` | Run unit tests only |
| `make test-integration`| Run integration tests only |
| `make test-security` | Run security and breach detection tests only |
| `make lint` | Run Ruff linter |
| `make format` | Format and auto-fix code with Ruff |
| `make typecheck` | Run Mypy strict static type checking |
| `make migrate` | Apply Alembic database migrations up to `head` |
| `make migration m="..."`| Generate a new autogenerated Alembic migration |
| `make seed` | Seed initial administrator user |
| `make docker-up` | Launch App, PostgreSQL, and Redis via Docker Compose |
| `make docker-down` | Stop Docker Compose containers |
| `make clean` | Clean test databases, caches, and build artifacts |

---

## Standardized API Error Contract

All errors return a consistent, machine-readable envelope:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "User with identifier '123' was not found.",
    "details": null,
    "request_id": "req_84a1e9e057f94bb8a113bc62729a9972"
  }
}
```

Validation failures include field-level error breakdowns in `details` without exposing internal Python traces.

---

## Security Architecture

1. **Password Hashing**: State-of-the-art Argon2id hashing with OWASP parameters.
2. **Access Tokens**: Short-lived JWTs (15 min) with allowlisted algorithms, issuer/audience validation, and unique `jti` tracking.
3. **Refresh Tokens**: Cryptographically random 32-byte tokens hashed with SHA-256 in the database.
4. **Breach Detection**: If a revoked refresh token is replayed, the system terminates the **entire token family**, preventing stolen credential persistence.
5. **Defense Headers**: Automatic `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, and HSTS in production.
6. **Mass Assignment Prevention**: Strict Pydantic schema separation ensures public registration endpoints cannot set administrative roles or flags.
7. **Production Gates**: Application configuration fails fast on startup if default insecure secret keys are detected in production environments.

---

## Adding New Features

Refer to [docs/feature-development.md](docs/feature-development.md) for the step-by-step workflow for creating new domain modules without altering global infrastructure.

---

## Documentation Index

- [Architecture & Boundaries](docs/architecture.md)
- [API Conventions & Error Contracts](docs/api-conventions.md)
- [Database & Migrations](docs/database.md)
- [Security & Threat Model](docs/security.md)
- [Testing Architecture](docs/testing.md)
- [Deployment & Kubernetes](docs/deployment.md)
- [Operations & Observability](docs/operations.md)
- [Troubleshooting Guide](docs/troubleshooting.md)
- [Step-by-Step Feature Development](docs/feature-development.md)
- [Architecture Decision Records (ADRs)](docs/decisions/)

---

## License

This project is licensed under the MIT License - see the LICENSE file for details.
# fastapi-base
# new-project
