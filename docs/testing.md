# Testing Architecture & Strategy

## 1. Multi-Tier Test Pyramid

The repository enforces a comprehensive automated test strategy:

```
           / \
          /API\       <- End-to-end endpoint tests (HTTP contracts, status codes, OpenAPI)
         /-----\
        / Integ \     <- Repository queries, transactions, soft-deletes, constraints
       /---------\
      /   Unit    \   <- Pure business logic, token hashing, error mapping, pagination
     /-------------\
```

1. **Unit Tests (`tests/unit/`)**:
   - `test_config.py`: Validates settings validation and production security gates.
   - `test_security.py`: Verifies Argon2id password hashing, SHA-256 tokens, JWT encode/decode, and expired token rejection.
   - `test_pagination.py`: Tests offset pagination math, zero-item handling, and cursor base64 serialization.
   - `test_errors.py`: Asserts exception status code mappings and standard error response schemas.

2. **Integration Tests (`tests/integration/`)**:
   - `test_database.py`: Tests explicit transactions, commit behavior, rollback upon exceptions, and soft-delete/restore lifecycles.
   - `test_repositories.py`: Tests `BaseRepository` and `UserRepository` queries, search filters, and database unique constraints.

3. **API Tests (`tests/api/`)**:
   - `test_health.py`: Validates liveness and readiness probe responses.
   - `test_auth.py`: Tests registration, login, token refresh rotation, logout, and password change.
   - `test_users.py`: Tests user profiles (`/users/me`), updates, admin user listings with pagination, and administrative controls.
   - `test_rate_limit.py`: Verifies rate limiting enforcement on login, checking HTTP 429 and `Retry-After`.
   - `test_idempotency.py`: Tests `Idempotency-Key` replay of identical requests and conflict rejection on payload modifications.

4. **Security Tests (`tests/security/`)**:
   - `test_auth_security.py`: Tests token family breach detection (revocation of entire family on reused token), privilege escalation defense, and cross-user resource protection.
   - `test_headers.py`: Validates injection of security defense headers and `X-Request-ID` propagation.

## 2. Test Execution Commands

```bash
# Run all tests
make test

# Run unit tests only
make test-unit

# Run integration tests only
make test-integration

# Run security tests only
make test-security

# Run tests with coverage reporting
pytest --cov=app --cov-report=term-missing
```

## 3. Test Isolation Guidelines

- Tests execute against an isolated in-memory SQLite database utilizing `StaticPool` and autouse table initialization fixtures (`prepare_database`).
- In-memory rate limiting and idempotency records are cleared between tests to prevent test pollution.
- Database dependencies in FastAPI endpoints are overridden using `app.dependency_overrides[get_db_session]`.
