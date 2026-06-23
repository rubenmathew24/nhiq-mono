# 04 — Dockerfiles

> **Claude instructions:** Create all files exactly as specified. All Dockerfiles go in the `docker/` folder at the repo root. The build context is always the repo root (`.`). Do not change paths.

---

## Key Principles

1. **Multi-stage builds** — separate build and runtime stages to minimize final image size
2. **Build context = repo root** — all `COPY` paths are relative to the repo root
3. **Non-root users** — all containers run as non-root for security
4. **Layer caching** — copy dependency files before source code so Docker caches dep installs
5. **`.dockerignore`** — each app has its own to keep contexts lean

---

## `docker/web.Dockerfile`

```dockerfile
# ── Stage 1: Install dependencies ─────────────────────────────────────────────
FROM node:20-alpine AS deps
WORKDIR /app

COPY apps/web/package.json apps/web/package-lock.json* ./
RUN npm ci --frozen-lockfile

# ── Stage 2: Build the Next.js app ────────────────────────────────────────────
FROM node:20-alpine AS builder
WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY apps/web/ .

# Build args for public env vars (set at build time in CI)
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

RUN npm run build

# ── Stage 3: Production runner ────────────────────────────────────────────────
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Create non-root user
RUN addgroup --system --gid 1001 nodejs \
 && adduser  --system --uid 1001 nextjs

# Copy only the standalone output (requires output: 'standalone' in next.config.ts)
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static    ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public          ./public

USER nextjs

EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
```

---

## `docker/api.Dockerfile`

```dockerfile
# ── Stage 1: Build dependencies ───────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# System libraries needed for geospatial packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgdal-dev \
    libpq-dev \
    gdal-bin \
    curl \
 && rm -rf /var/lib/apt/lists/*

COPY apps/api/requirements.txt .

# Install to a prefix we can copy cleanly
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: Runtime ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Runtime system libraries only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgdal-dev \
    libpq5 \
    curl \
 && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Create non-root user
RUN addgroup --system --gid 1001 apigroup \
 && adduser  --system --uid 1001 --ingroup apigroup apiuser

COPY --chown=apiuser:apigroup apps/api/ .

USER apiuser

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

---

## `docker/worker.Dockerfile`

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgdal-dev \
    libpq-dev \
    gdal-bin \
    curl \
 && rm -rf /var/lib/apt/lists/*

COPY workers/ingest/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN addgroup --system --gid 1001 workergroup \
 && adduser  --system --uid 1001 --ingroup workergroup workeruser

COPY --chown=workeruser:workergroup workers/ .

USER workeruser

# Default — override in docker compose or Container Apps Job
CMD ["python", "-m", "ingest.epa.run"]
```

---

## `.dockerignore` Files

### `apps/web/.dockerignore`
```
node_modules/
.next/
out/
.env
.env.*
*.log
.DS_Store
README.md
```

### `apps/api/.dockerignore`
```
__pycache__/
*.pyc
*.pyo
.venv/
venv/
.env
.env.*
*.log
.pytest_cache/
.ruff_cache/
htmlcov/
migrations/
README.md
```

### `workers/.dockerignore`
```
__pycache__/
*.pyc
.venv/
.env
.env.*
*.log
README.md
```

---

## `docker-compose.yml` (Local Dev — Full)

```yaml
services:

  # ── Frontend ────────────────────────────────────────────────────────────────
  web:
    build:
      context: .
      dockerfile: docker/web.Dockerfile
      target: runner
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
      NEXTAUTH_SECRET: ${NEXTAUTH_SECRET:-local-dev-secret-change-me}
      NEXTAUTH_URL: http://localhost:3000
    depends_on:
      api:
        condition: service_healthy
    restart: unless-stopped

  # ── API ─────────────────────────────────────────────────────────────────────
  api:
    build:
      context: .
      dockerfile: docker/api.Dockerfile
      target: runtime
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://postgres:postgres@db:5432/neighborhoodiq
      REDIS_URL: redis://redis:6379
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:-}
      MAPBOX_TOKEN: ${MAPBOX_TOKEN:-}
      ENVIRONMENT: development
      LOG_LEVEL: INFO
    volumes:
      # Hot reload in dev — mount source over the container's copy
      - ./apps/api:/app
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 20s
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    restart: unless-stopped

  # ── Database ─────────────────────────────────────────────────────────────────
  db:
    image: postgis/postgis:16-3.4
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: neighborhoodiq
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./infra/sql/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 10

  # ── Redis ─────────────────────────────────────────────────────────────────────
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data
    command: redis-server --appendonly yes

  # ── Workers (run on-demand with --profile workers) ───────────────────────────
  worker-epa:
    build:
      context: .
      dockerfile: docker/worker.Dockerfile
    environment:
      DATABASE_URL: postgresql://postgres:postgres@db:5432/neighborhoodiq
      EPA_AQS_EMAIL: ${EPA_AQS_EMAIL:-}
      EPA_AQS_KEY: ${EPA_AQS_KEY:-}
    command: python -m ingest.epa.run
    depends_on:
      db:
        condition: service_healthy
    profiles:
      - workers

  worker-census:
    build:
      context: .
      dockerfile: docker/worker.Dockerfile
    environment:
      DATABASE_URL: postgresql://postgres:postgres@db:5432/neighborhoodiq
      CENSUS_API_KEY: ${CENSUS_API_KEY:-}
    command: python -m ingest.census.run
    depends_on:
      db:
        condition: service_healthy
    profiles:
      - workers

volumes:
  pgdata:
  redisdata:
```

---

## `docker-compose.prod.yml` (Production Overrides)

```yaml
# Use with: docker compose -f docker-compose.yml -f docker-compose.prod.yml up
# In Azure, images come from ACR — no build step.

services:
  web:
    image: ${ACR_LOGIN_SERVER}/neighborhoodiq-web:${IMAGE_TAG}
    build: !reset null    # Don't build in prod
    volumes: !reset []    # No volume mounts in prod

  api:
    image: ${ACR_LOGIN_SERVER}/neighborhoodiq-api:${IMAGE_TAG}
    build: !reset null
    volumes: !reset []    # No hot-reload volume mounts
    environment:
      ENVIRONMENT: production
      LOG_LEVEL: WARNING
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## Useful Docker Commands

```bash
# Build all images
docker compose build

# Build a single image
docker compose build api

# Start everything (foreground)
docker compose up

# Start in background
docker compose up -d

# Start with workers
docker compose --profile workers up

# Rebuild and restart a single service
docker compose up --build api

# View logs for one service
docker compose logs -f api

# Open a shell in the running API container
docker exec -it $(docker compose ps -q api) /bin/bash

# Run a one-off command (e.g. migrations)
docker compose run --rm api alembic upgrade head

# Run a specific worker once
docker compose run --rm worker-epa

# Stop everything and remove volumes (wipe DB)
docker compose down -v

# Check image sizes
docker images | grep neighborhoodiq

# Prune unused images/containers
docker system prune -f
```

---

## Checklist

- [ ] `docker/web.Dockerfile` builds without errors
- [ ] `docker/api.Dockerfile` builds without errors
- [ ] `docker/worker.Dockerfile` builds without errors
- [ ] All three `.dockerignore` files in place
- [ ] `docker compose up` starts all services (web, api, db, redis)
- [ ] `docker compose --profile workers up` adds workers
- [ ] `/health` responds from api container
- [ ] `localhost:3000` responds from web container
- [ ] No secrets hardcoded in any Dockerfile
- [ ] Images run as non-root user
