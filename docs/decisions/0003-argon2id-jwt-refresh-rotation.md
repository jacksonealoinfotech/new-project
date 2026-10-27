# ADR 0003: Argon2id Password Hashing and Refresh Token Rotation with Breach Detection

## Status
Accepted

## Context
Traditional password-hashing schemes (MD5, SHA-256, plain PBKDF2) are vulnerable to hardware-accelerated attacks. In addition, stateless long-lived JWTs cannot be revoked if stolen, while stateful session lookups on every request add database latency.

## Decision
1. We mandate **Argon2id** (`argon2-cffi`) for all password hashing following OWASP recommendations.
2. We implement **hybrid token authentication**:
   - Short-lived JWT access tokens (15 minutes) for high-performance stateless verification.
   - Long-lived rotatable refresh tokens (7 days) persisted as SHA-256 hashes in PostgreSQL.
3. Every refresh token is tagged with a `family_id`. When a token is refreshed, it is immediately revoked and a new token in the same family is issued. If a revoked token is ever presented again, the system identifies a breach and revokes all active tokens in that entire session family.

## Consequences
- **Positive**: State-of-the-art password defense against GPU/ASIC crackers.
- **Positive**: Immediate compromise containment upon stolen token reuse.
- **Negative**: Adds a database round-trip during refresh operations (every 15 minutes per active user), which is negligible compared to standard API traffic.
