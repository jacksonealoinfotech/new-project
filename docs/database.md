# Database Architecture & Migration Guidelines

## 1. Asynchronous SQLAlchemy 2.x Architecture

The template leverages SQLAlchemy 2.x with full asynchronous I/O (`AsyncEngine` and `AsyncSession`).
- In production and staging: `postgresql+asyncpg://...`
- In local testing and fast CI runs: `sqlite+aiosqlite://...`

### Connection Pooling Strategy
- **PostgreSQL**: Managed via `AsyncAdaptedQueuePool` with pre-ping validation enabled to automatically drop stale connections.
- **SQLite**: Managed via `NullPool` to prevent cross-thread file locks during concurrent tests.

## 2. Model Design Conventions

Every persistent model inherits from `app.db.base.Base` and leverages standardized mixins:

1. **`UUIDPrimaryKeyMixin`**: Enforces random UUID v4 primary keys across all tables. Avoids enumeration attacks and simplifies cross-system distribution.
2. **`TimestampMixin`**: Provides UTC timezone-aware `created_at` and `updated_at` timestamps using database server default triggers.
3. **`SoftDeleteMixin`**: Implements logical deletion (`is_deleted: bool` and `deleted_at: datetime | None`). Query methods filter out soft-deleted records by default.
4. **`VersionMixin`**: Tracks optimistic concurrency counter (`version: int`) to prevent lost concurrent updates.

## 3. Transaction Rules

```python
# CORRECT: Application Service manages the transaction boundary
async with in_transaction(self.session):
    user = await self.user_repo.create(user_instance)
    outbox_msg = await self.outbox_repo.enqueue("user.registered", payload)
    # Both statements commit atomically upon exiting the context block!
```

- Repositories call `await session.flush()` to populate generated attributes and evaluate constraints.
- Repositories **never** call `await session.commit()`.
- Unhandled exceptions automatically trigger rollbacks.

## 4. Alembic Migrations

### Running Migrations
```bash
# Upgrade database to head
make migrate
# Or: alembic upgrade head
```

### Generating Migrations
```bash
# Autogenerate migration from model changes
make migration m="add_user_profile_bio"
# Or: alembic revision --autogenerate -m "add_user_profile_bio"
```

### Production Zero-Downtime Rule (Expand and Contract)
1. **Never drop columns or tables in an active deployment**.
2. **Phase 1 (Expand)**: Add new nullable columns or tables. Deploy application reading both formats.
3. **Phase 2 (Migrate Data)**: Backfill data asynchronously.
4. **Phase 3 (Contract)**: Drop old unused columns in a subsequent release.
