# System Architecture

## 1. Overview and Architectural Pattern

This repository implements a **Feature-Oriented Modular Monolith** designed for high throughput, clean dependency boundaries, and rapid extensibility. Rather than forcing distributed microservice complexity onto early and mid-stage systems, the codebase encapsulates business domains inside feature modules while sharing robust core platform infrastructure.

```
API Transport Layer (FastAPI Routers & OpenAPI)
         ↓
Application Service Layer (Use Cases & Transaction Coordination)
         ↓
Domain Rules & Validation (Entities, Enums, Permissions)
         ↓
Infrastructure & Persistence (SQLAlchemy 2.x, Repositories, Redis, HTTPX)
```

## 2. Directory Hierarchy and Layer Responsibilities

```
fastapi-production-template/
├── app/
│   ├── api/                   # Transport routing, global dependencies, API version prefixes
│   │   ├── v1/                # Version 1 routing registry
│   │   │   └── endpoints/     # Cross-cutting endpoints (health checks, liveness/readiness)
│   ├── common/                # Shared domain primitives (enums, base schemas, utility helpers)
│   ├── core/                  # Core runtime infrastructure (config, logging, security, errors, middleware)
│   ├── db/                    # SQLAlchemy async engine, session lifecycle, declarative base, transaction mixins
│   ├── infrastructure/        # External backing service adapters (Redis, Cache, HTTP client, Outbox, Storage)
│   ├── modules/               # Feature-oriented domain modules
│   │   ├── auth/              # Authentication, tokens, login/refresh/logout, breach detection
│   │   └── users/             # User domain, profiles, RBAC, administrative controls
│   ├── repositories/          # Generic BaseRepository abstraction and protocols
│   └── main.py                # FastAPI application factory and entry point
├── alembic/                   # Database migrations (async runner, autogenerate scripts)
├── docs/                      # Architectural documentation and ADRs
├── scripts/                   # Operational utilities (seed, migrate, test)
└── tests/                     # Multi-tier test suite (unit, integration, API, security)
```

## 3. Strict Boundary Rules

1. **Thin Routers**: Router endpoints validate incoming HTTP inputs and delegate business workflows immediately to application services. Routes do not execute raw queries.
2. **Explicit Transactions**: Repositories flush changes to establish identity and constraints, but **never commit**. Transactions are owned explicitly by services via `async with in_transaction(session):`.
3. **No Direct ORM Exposure**: SQLAlchemy models are never returned directly to API clients. Dedicated Pydantic response models filter attributes and strip internal credentials.
4. **Mass-Assignment Defense**: Input schemas strictly separate self-service user fields from administrative privileges (e.g., `role`, `is_active`, `is_verified` cannot be set via public registration).
5. **Decoupled Backing Services**: Redis, external email, object storage, and background processing are defined through clean protocol adapters and remain optional.
