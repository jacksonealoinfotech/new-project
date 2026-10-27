# ADR 0005: Decoupled Backing Services (Redis, Outbox, and Caching)

## Status
Accepted

## Context
Many backend starter templates fail to run out of the box because they mandate running instances of Redis, Celery, RabbitMQ, and external S3 buckets immediately upon cloning the repository. This creates steep onboarding hurdles for local development and lightweight testing environments.

## Decision
1. Backing infrastructure components (Redis, Cache, Email, Storage) are defined via clean Python protocols (`typing.Protocol`).
2. High-performance in-memory implementations are provided as seamless fallbacks when external services are disabled (`REDIS_ENABLED=false`).
3. Projects can toggle Redis, durable outbox publishers, and S3 adapters via configuration flags without changing business code.

## Consequences
- **Positive**: Zero external dependencies required to clone, run migrations, execute tests, and run local development servers.
- **Positive**: Clean path to production scaling by simply toggling `REDIS_ENABLED=true` in staging and production.
- **Negative**: In-memory rate limiting and caching do not synchronize across multiple multi-process workers; production multi-pod deployments must enable Redis.
