# Deployment & Container Operations

## 1. Container Architecture

The production `Dockerfile` uses a two-stage build to minimize image size and eliminate build toolchains from the final runtime container:

- **Stage 1 (Builder)**: Installs compilation toolchains (`build-essential`, `libpq-dev`), builds a clean virtual environment in `/opt/venv`, and installs dependencies.
- **Stage 2 (Runtime)**: Copies `/opt/venv` into a slim Debian image, runs as a dedicated non-root user (`appuser`, UID 10001), and embeds container health probes.

```bash
# Build the production image
docker build -t fastapi-backend:latest .

# Run the container
docker run -p 8000:8000 \
  -e APP_ENV=production \
  -e SECRET_KEY="<strong-random-key>" \
  -e JWT_SECRET_KEY="<strong-random-jwt-key>" \
  -e DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/db" \
  fastapi-backend:latest
```

## 2. Kubernetes Readiness and Liveness Probes

Configure Kubernetes pod definitions as follows:

```yaml
livenessProbe:
  httpGet:
    path: /api/v1/health/liveness
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 15
  timeoutSeconds: 3

readinessProbe:
  httpGet:
    path: /api/v1/health/readiness
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
  timeoutSeconds: 5
```

- **Liveness**: Validates process execution without calling external databases to avoid cascading restarts during DB network blips.
- **Readiness**: Validates that database and required backing connections are functional before Kubernetes routes traffic to the pod.

## 3. Production Deployment Checklist

1. [ ] Inject secrets via AWS Secrets Manager, HashiCorp Vault, or GCP Secret Manager. Never bake secrets into container images or `.env` files.
2. [ ] Execute database migrations before switching production traffic (`alembic upgrade head`).
3. [ ] Set `APP_ENV=production` and `APP_DEBUG=false`.
4. [ ] Configure `ALLOWED_CORS_ORIGINS` to trusted frontend domains only (no wildcard `*`).
5. [ ] Configure `ALLOWED_HOSTS` to valid domain names.
6. [ ] Set `LOG_FORMAT=json` for automated ingestion into Datadog, CloudWatch, or Grafana Loki.
