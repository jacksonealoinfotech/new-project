# ADR 0004: Centralized Exception Hierarchy and Machine-Readable Error Contract

## Status
Accepted

## Context
Default framework error handling in many APIs leads to inconsistent response formats: validation failures return one structure, unhandled 500s return raw HTML or leak internal stack traces, and third-party exceptions expose database credentials and SQL statements to users.

## Decision
1. We define an explicit application exception hierarchy inheriting from `ApplicationError` with machine-readable `ErrorCode` constants and HTTP status codes.
2. Centralized exception handlers map all errors into a standardized JSON response:
   ```json
   {
     "error": {
       "code": "ERROR_CODE",
       "message": "Human-readable explanation",
       "details": null,
       "request_id": "req_uuid"
     }
   }
   ```
3. Database `IntegrityError` is intercepted and sanitized into safe 409/400 errors without leaking SQL statements. Unhandled 500 exceptions log the full traceback internally with `request_id` while returning a generic message to clients.

## Consequences
- **Positive**: Consistent client SDK integration; frontend applications can switch on deterministic `error.code` strings rather than brittle message parsing.
- **Positive**: Strict data sanitization prevents internal database credentials and tracebacks from leaking.
- **Negative**: Requires engineers to define domain errors instead of scattering arbitrary `HTTPException` raises throughout the code.
