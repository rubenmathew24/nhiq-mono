# 05 — CI/CD Pipeline

> **Claude instructions:** Create all files in `.github/workflows/`. Secrets are set in GitHub → Settings → Secrets and Variables → Actions. Never hardcode credentials.

---

## Overview

```
Push to feature branch  →  CI (lint + test)
PR to main              →  CI (lint + test) + preview comment
Merge to main           →  CI → Build images → Push to ACR → Deploy to Azure Container Apps
```

---

## Required GitHub Secrets

Set these in GitHub → Repo → Settings → Secrets and Variables → Actions:

| Secret | Description |
|---|---|
| `ACR_LOGIN_SERVER` | e.g. `neighborhoodiq.azurecr.io` |
| `ACR_USERNAME` | Azure Container Registry username |
| `ACR_PASSWORD` | Azure Container Registry password |
| `AZURE_CREDENTIALS` | JSON from `az ad sp create-for-rbac` (see below) |
| `AZURE_RESOURCE_GROUP` | e.g. `neighborhoodiq-rg` |
| `AZURE_CONTAINER_APP_WEB` | Container App name for web, e.g. `niq-web` |
| `AZURE_CONTAINER_APP_API` | Container App name for api, e.g. `niq-api` |
| `ANTHROPIC_API_KEY` | For runtime environment injection |
| `MAPBOX_TOKEN` | For Next.js build arg |
| `NEXT_PUBLIC_API_URL` | e.g. `https://api.neighborhoodiq.com` |

### Generate `AZURE_CREDENTIALS`

```bash
az ad sp create-for-rbac \
  --name "neighborhoodiq-github-actions" \
  --role contributor \
  --scopes /subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RESOURCE_GROUP> \
  --json-auth
```

Paste the JSON output as the `AZURE_CREDENTIALS` secret.

---

## `.github/workflows/ci.yml` — Lint & Test (All Branches)

```yaml
name: CI

on:
  push:
    branches: ["**"]
  pull_request:
    branches: [main]

jobs:
  # ── Python / FastAPI ─────────────────────────────────────────────────────────
  api-lint-test:
    name: API — Lint & Test
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgis/postgis:16-3.4
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: neighborhoodiq_test
        ports: ["5432:5432"]
        options: >-
          --health-cmd="pg_isready -U postgres"
          --health-interval=5s
          --health-timeout=5s
          --health-retries=10

      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]

    defaults:
      run:
        working-directory: apps/api

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"
          cache-dependency-path: apps/api/requirements.txt

      - name: Install dependencies
        run: pip install -r requirements.txt && pip install pytest pytest-asyncio httpx ruff black

      - name: Lint (ruff)
        run: ruff check .

      - name: Format check (black)
        run: black --check .

      - name: Run tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/neighborhoodiq_test
          REDIS_URL: redis://localhost:6379
          ENVIRONMENT: test
          ANTHROPIC_API_KEY: test-key-not-real
          MAPBOX_TOKEN: test-key-not-real
          SECRET_KEY: test-secret-key
        run: pytest tests/ -v --tb=short

  # ── TypeScript / Next.js ─────────────────────────────────────────────────────
  web-lint-build:
    name: Web — Lint & Build
    runs-on: ubuntu-latest

    defaults:
      run:
        working-directory: apps/web

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: apps/web/package-lock.json

      - name: Install dependencies
        run: npm ci

      - name: Lint
        run: npm run lint

      - name: Type check
        run: npx tsc --noEmit

      - name: Build
        env:
          NEXT_PUBLIC_API_URL: http://localhost:8000
        run: npm run build
```

---

## `.github/workflows/deploy.yml` — Build & Deploy (main branch only)

```yaml
name: Deploy

on:
  push:
    branches: [main]

env:
  IMAGE_TAG: ${{ github.sha }}

jobs:
  # ── Build & Push Docker Images ───────────────────────────────────────────────
  build-and-push:
    name: Build & Push to ACR
    runs-on: ubuntu-latest

    outputs:
      image_tag: ${{ env.IMAGE_TAG }}

    steps:
      - uses: actions/checkout@v4

      - name: Log in to Azure Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ secrets.ACR_LOGIN_SERVER }}
          username: ${{ secrets.ACR_USERNAME }}
          password: ${{ secrets.ACR_PASSWORD }}

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      # Web image
      - name: Build & push web
        uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/web.Dockerfile
          push: true
          tags: |
            ${{ secrets.ACR_LOGIN_SERVER }}/neighborhoodiq-web:${{ env.IMAGE_TAG }}
            ${{ secrets.ACR_LOGIN_SERVER }}/neighborhoodiq-web:latest
          build-args: |
            NEXT_PUBLIC_API_URL=${{ secrets.NEXT_PUBLIC_API_URL }}
          cache-from: type=gha,scope=web
          cache-to: type=gha,scope=web,mode=max

      # API image
      - name: Build & push api
        uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/api.Dockerfile
          push: true
          tags: |
            ${{ secrets.ACR_LOGIN_SERVER }}/neighborhoodiq-api:${{ env.IMAGE_TAG }}
            ${{ secrets.ACR_LOGIN_SERVER }}/neighborhoodiq-api:latest
          cache-from: type=gha,scope=api
          cache-to: type=gha,scope=api,mode=max

      # Worker image
      - name: Build & push worker
        uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/worker.Dockerfile
          push: true
          tags: |
            ${{ secrets.ACR_LOGIN_SERVER }}/neighborhoodiq-worker:${{ env.IMAGE_TAG }}
            ${{ secrets.ACR_LOGIN_SERVER }}/neighborhoodiq-worker:latest
          cache-from: type=gha,scope=worker
          cache-to: type=gha,scope=worker,mode=max

  # ── Deploy API ───────────────────────────────────────────────────────────────
  deploy-api:
    name: Deploy API to Azure Container Apps
    runs-on: ubuntu-latest
    needs: build-and-push

    steps:
      - uses: actions/checkout@v4

      - name: Azure Login
        uses: azure/login@v2
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Deploy API Container App
        uses: azure/container-apps-deploy-action@v1
        with:
          containerAppName: ${{ secrets.AZURE_CONTAINER_APP_API }}
          resourceGroup: ${{ secrets.AZURE_RESOURCE_GROUP }}
          imageToDeploy: ${{ secrets.ACR_LOGIN_SERVER }}/neighborhoodiq-api:${{ env.IMAGE_TAG }}

  # ── Run DB Migrations ────────────────────────────────────────────────────────
  run-migrations:
    name: Run Database Migrations
    runs-on: ubuntu-latest
    needs: deploy-api

    steps:
      - uses: actions/checkout@v4

      - name: Azure Login
        uses: azure/login@v2
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Run Alembic migrations
        uses: azure/container-apps-run-action@v1    # or az containerapp exec
        with:
          containerAppName: ${{ secrets.AZURE_CONTAINER_APP_API }}
          resourceGroup: ${{ secrets.AZURE_RESOURCE_GROUP }}
          command: "alembic upgrade head"

  # ── Deploy Web ───────────────────────────────────────────────────────────────
  deploy-web:
    name: Deploy Web to Azure Container Apps
    runs-on: ubuntu-latest
    needs: deploy-api    # Web depends on API being healthy first

    steps:
      - uses: actions/checkout@v4

      - name: Azure Login
        uses: azure/login@v2
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Deploy Web Container App
        uses: azure/container-apps-deploy-action@v1
        with:
          containerAppName: ${{ secrets.AZURE_CONTAINER_APP_WEB }}
          resourceGroup: ${{ secrets.AZURE_RESOURCE_GROUP }}
          imageToDeploy: ${{ secrets.ACR_LOGIN_SERVER }}/neighborhoodiq-web:${{ env.IMAGE_TAG }}
```

---

## `.github/workflows/worker-schedule.yml` — Scheduled Ingestion Jobs

```yaml
name: Data Ingestion Workers

on:
  schedule:
    - cron: "0 2 * * *"      # Daily at 2am UTC — EPA AQI
    - cron: "0 3 * * 0"      # Weekly Sundays — FBI crime, Census
    - cron: "0 4 1 * *"      # Monthly 1st — FEMA, CMS, Zillow
  workflow_dispatch:          # Allow manual trigger from GitHub UI
    inputs:
      worker:
        description: "Which worker to run"
        required: true
        type: choice
        options:
          - epa
          - fbi
          - census
          - fema
          - cms
          - zillow
          - all

jobs:
  run-worker:
    name: Run ${{ github.event.inputs.worker || 'scheduled' }} worker
    runs-on: ubuntu-latest

    steps:
      - name: Azure Login
        uses: azure/login@v2
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Trigger Container Apps Job — EPA
        if: github.event_name == 'schedule' || github.event.inputs.worker == 'epa' || github.event.inputs.worker == 'all'
        run: |
          az containerapp job start \
            --name niq-worker-epa \
            --resource-group ${{ secrets.AZURE_RESOURCE_GROUP }}

      - name: Trigger Container Apps Job — Census
        if: github.event_name == 'schedule' || github.event.inputs.worker == 'census' || github.event.inputs.worker == 'all'
        run: |
          az containerapp job start \
            --name niq-worker-census \
            --resource-group ${{ secrets.AZURE_RESOURCE_GROUP }}
```

---

## Testing Locally Before Pushing

```bash
# Run linting manually
cd apps/api && ruff check . && black --check .
cd apps/web && npm run lint && npx tsc --noEmit

# Run API tests
cd apps/api && pytest tests/ -v

# Simulate a full build (what CI does)
docker build -f docker/web.Dockerfile -t niq-web-test .
docker build -f docker/api.Dockerfile -t niq-api-test .
docker build -f docker/worker.Dockerfile -t niq-worker-test .
```

---

## Branch Protection Rules

Set these in GitHub → Repo → Settings → Branches → Add rule for `main`:

- [x] Require status checks to pass before merging
  - Required checks: `API — Lint & Test`, `Web — Lint & Build`
- [x] Require pull request before merging
- [x] Require at least 1 approval
- [x] Do not allow bypassing the above settings

---

## Checklist

- [ ] `.github/workflows/ci.yml` created
- [ ] `.github/workflows/deploy.yml` created
- [ ] `.github/workflows/worker-schedule.yml` created
- [ ] All GitHub secrets set (ACR, Azure, API keys)
- [ ] `AZURE_CREDENTIALS` JSON generated and stored
- [ ] CI passes on first push
- [ ] Branch protection rules set on `main`
- [ ] Manual worker trigger works from GitHub Actions UI
