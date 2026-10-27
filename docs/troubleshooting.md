# Operational Troubleshooting Guide

## 1. Common Issues and Resolutions

### Issue: "Greenlet error / greenlet_spawn has not been called"
- **Cause**: Attempting to execute synchronous SQLAlchemy operations inside an async event loop, or missing `greenlet` dependency.
- **Fix**: Ensure all persistence calls use async methods (`await session.execute(...)`, `await repo.get(...)`), and verify `greenlet` is installed (`pip install greenlet`).

### Issue: "Database connection timed out or pool exhausted"
- **Cause**: Database transactions held open during slow external HTTP calls or leaked sessions.
- **Fix**: Never make external HTTP requests while holding open database locks or transactions. Check pool metrics and tune `DATABASE_POOL_SIZE` and `DATABASE_MAX_OVERFLOW`.

### Issue: "pydantic_settings.exceptions.SettingsError on ALLOWED_CORS_ORIGINS"
- **Cause**: Passing a plain comma-separated string in `.env` without validator handling.
- **Fix**: The template includes a field validator supporting both comma-delimited strings and JSON lists in environment configurations.

### Issue: "Token verification failed / 401 Unauthorized"
- **Cause**: Clock skew between servers, expired token, or mismatched `JWT_ISSUER`/`JWT_AUDIENCE` configurations.
- **Fix**: Check system NTP synchronization and confirm `JWT_ISSUER` and `JWT_AUDIENCE` match environment variables.

### Issue: "409 IDEMPOTENCY_CONFLICT"
- **Cause**: Client retried a request with the same `Idempotency-Key` but modified the payload body, or the original request is still actively processing.
- **Fix**: If retrying after a network failure, send the exact identical payload. If the previous request is in-flight, implement exponential backoff before retrying.
