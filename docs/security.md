# Security Architecture & Threat Model

## 1. Authentication Security

### Argon2id Password Hashing
Passwords are never hashed using outdated algorithms (MD5, SHA-1, plain bcrypt). The application utilizes `argon2-cffi` configured with recommended OWASP memory-hard parameters resistant to GPU/ASIC cracking.

### Short-Lived JWT Access Tokens
- Lifespan: Default 15 minutes.
- Strict algorithm allowlist (`HS256`, `RS256`).
- Mandated claims: `exp` (expiration), `iat` (issued at), `iss` (issuer), `aud` (audience), `sub` (subject UUID), and `jti` (unique JWT ID).

### Refresh Token Rotation and Breach Detection
Refresh tokens are high-value credentials. The platform defends against refresh token theft via **automatic token family invalidation**:
1. Refresh tokens are generated using `secrets.token_urlsafe(32)`.
2. Raw refresh tokens are never persisted in plain text; only SHA-256 hashes are stored in the database.
3. Every token belongs to a cryptographic `family_id`.
4. When a refresh token is used, it is revoked and a new refresh token is issued into the same family.
5. **Breach Detection**: If an adversary replays an already-revoked refresh token, the system flags a compromise and immediately revokes all active tokens in that entire family, terminating the adversary's session.

## 2. Authorization and RBAC

- Roles: `USER`, `ADMIN`, `SUPERUSER`.
- Public registration endpoints (`/auth/register`) strictly prohibit role assignment.
- Role requirements are declared on routes via `dependencies=[Depends(require_role(UserRole.ADMIN))]`.
- Ownership verification ensures non-admin users cannot access or mutate resources belonging to other principals.

## 3. Defense-in-Depth HTTP Headers

Every response is injected with security headers via `SecurityHeadersMiddleware`:
- `X-Content-Type-Options: nosniff`: Prevents MIME-sniffing exploits.
- `X-Frame-Options: DENY`: Prevents clickjacking.
- `Referrer-Policy: strict-origin-when-cross-origin`: Restricts sensitive URL parameter leakage.
- `Permissions-Policy`: Restricts camera, microphone, and geolocation.
- `Strict-Transport-Security` (Production): Enforces HSTS for 1 year.
- `Content-Security-Policy` (Production): Restricts script execution to same-origin.

## 4. Rate Limiting and Anti-Abuse

- Endpoints apply rate limits (e.g., maximum 10 login attempts per 60 seconds).
- Exceeded thresholds return HTTP 429 `RATE_LIMIT_EXCEEDED` with a `Retry-After` header.
- Client identity is determined by authenticated `user_id` or sanitized forwarded IP.

## 5. Secret Protection & Sanitization

- Production environments fail fast on startup if `SECRET_KEY` or `JWT_SECRET_KEY` contain default insecure strings.
- Logging pipelines automatically scrub fields matching `password`, `token`, `secret`, `authorization`, `cookie`, and `api_key`.
- Database error handlers intercept `IntegrityError` to prevent raw SQL strings or table schema details from leaking to clients.
