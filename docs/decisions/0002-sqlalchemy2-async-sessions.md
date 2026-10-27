# ADR 0002: SQLAlchemy 2.x Asynchronous Sessions and Transaction Ownership

## Status
Accepted

## Context
High-concurrency web APIs require non-blocking I/O to maximize throughput on modern async runtimes like ASGI/FastAPI. Mixing synchronous database drivers into async endpoints blocks the asyncio event loop, severely degrading request concurrency. Furthermore, many architectures perform hidden commits inside repository methods, making multi-step atomic operations impossible.

## Decision
1. We mandate **SQLAlchemy 2.x asynchronous I/O** across all database interactions using `create_async_engine`, `async_sessionmaker`, and `AsyncSession`.
2. Repositories are strictly data mappers: they execute `select`, `add`, `flush`, but **never commit**.
3. Transactions are explicitly owned by Application Services using the `async with in_transaction(session):` context manager.

## Consequences
- **Positive**: Full event-loop concurrency without thread-blocking stalls.
- **Positive**: Clean transaction boundaries; multi-step business logic can roll back atomically if any step fails.
- **Negative**: Requires careful async discipline; asynchronous lazy loading requires explicit `selectinload` or `joinedload` to prevent greenlet context errors.
