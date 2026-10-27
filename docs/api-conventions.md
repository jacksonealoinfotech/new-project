# API Conventions and Error Contracts

## 1. Versioning and Route Layout

All business endpoints are versioned under `/api/v1`. Changes that introduce breaking schema alterations must be deployed under a subsequent version prefix (e.g., `/api/v2`).

- Health probes are located at `/api/v1/health/liveness` and `/api/v1/health/readiness`.
- Authentication operations are grouped at `/api/v1/auth/*`.
- Resource management operations are grouped at `/api/v1/<resource>/*`.

## 2. Standardized Error Contract

All non-2xx responses adhere strictly to the following envelope:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "User with identifier '...' was not found.",
    "details": null,
    "request_id": "req_84a1e9e057f94bb8a113bc62729a9972"
  }
}
```

### Error Codes
| Error Code | HTTP Status | Description |
| :--- | :--- | :--- |
| `AUTHENTICATION_FAILED` | 401 | Missing, expired, invalid, or forged credentials |
| `PERMISSION_DENIED` | 403 | Principal lacks required role or resource ownership |
| `RESOURCE_NOT_FOUND` | 404 | Target entity does not exist or has been soft-deleted |
| `RESOURCE_CONFLICT` | 409 | Unique constraint or state conflict |
| `IDEMPOTENCY_CONFLICT` | 409 | Reused Idempotency-Key with conflicting payload |
| `CONCURRENCY_CONFLICT` | 409 | Optimistic locking version mismatch |
| `VALIDATION_ERROR` | 422 | Request body or query parameters failed schema rules |
| `RATE_LIMIT_EXCEEDED` | 429 | Rate limit quota exceeded |
| `EXTERNAL_SERVICE_ERROR`| 502 | Third-party upstream service failure |
| `DATABASE_UNAVAILABLE` | 503 | Database connection pool exhausted or down |
| `INTERNAL_SERVER_ERROR`| 500 | Unhandled internal exception (traceback hidden) |

## 3. Standardized Pagination Contracts

### Offset Pagination
```json
{
  "items": [ ... ],
  "meta": {
    "page": 1,
    "page_size": 20,
    "total_items": 142,
    "total_pages": 8,
    "has_next": true,
    "has_previous": false
  }
}
```

### Cursor Pagination
```json
{
  "items": [ ... ],
  "meta": {
    "next_cursor": "eyJpZCI6ICIxMjMiLCAidHMiOiAiMjAyNi0xMC0xMCJ9",
    "previous_cursor": null,
    "has_next": true
  }
}
```

## 4. HTTP Headers

| Header | Direction | Description |
| :--- | :--- | :--- |
| `X-Request-ID` | Request & Response | End-to-end distributed tracking identifier |
| `Idempotency-Key` | Request | Unique client key for safe operation replay |
| `X-RateLimit-Limit` | Response | Permitted requests in active window |
| `X-RateLimit-Remaining`| Response | Available requests remaining |
| `Retry-After` | Response | Seconds to wait when receiving HTTP 429 |
