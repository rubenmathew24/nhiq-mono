# 01 — Monorepo Setup

> **Claude instructions:** Execute every command block in order. After each major section, confirm the output matches what's expected before continuing. Ask the user before overwriting any existing files.

---

## Prerequisites

Verify these are installed before starting:

```bash
node --version        # must be >= 20
python --version      # must be >= 3.12
docker --version      # must be >= 24
git --version
```

---

## Step 1: Initialize the Repository

```bash
mkdir neighborhoodiq && cd neighborhoodiq
git init
echo "# NeighborhoodIQ" > README.md
```

---

## Step 2: Create Directory Structure

```bash
mkdir -p apps/web
mkdir -p apps/api
mkdir -p workers/ingest/cms
mkdir -p workers/ingest/epa
mkdir -p workers/ingest/fema
mkdir -p workers/ingest/fbi
mkdir -p workers/ingest/census
mkdir -p workers/ingest/zillow
mkdir -p workers/scoring
mkdir -p packages/shared-types
mkdir -p docker
mkdir -p infra/bicep
mkdir -p docs
mkdir -p .github/workflows
```

---

## Step 3: Root .gitignore

Create `.gitignore` at the repo root:

```gitignore
# Environment
.env
.env.local
.env.*.local

# Python
__pycache__/
*.py[cod]
*.pyo
.venv/
venv/
*.egg-info/
dist/
.pytest_cache/
.ruff_cache/

# Node
node_modules/
.next/
out/
.turbo/

# Docker
*.log

# OS
.DS_Store
Thumbs.db

# IDE
.vscode/settings.json
.idea/

# Azure
*.tfstate
*.tfstate.backup

# Coverage
htmlcov/
.coverage
coverage.xml
```

---

## Step 4: Root .env.example

Create `.env.example` at the repo root (this is committed to git as a template):

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@db:5432/neighborhoodiq

# Redis
REDIS_URL=redis://redis:6379

# Claude AI
ANTHROPIC_API_KEY=

# Mapbox (geocoding + maps)
MAPBOX_TOKEN=

# Next.js
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXTAUTH_SECRET=
NEXTAUTH_URL=http://localhost:3000

# Azure Storage (PDF exports)
AZURE_STORAGE_CONNECTION_STRING=
AZURE_STORAGE_CONTAINER_NAME=reports

# External Data APIs
EPA_AQS_EMAIL=
EPA_AQS_KEY=
FBI_API_KEY=
CENSUS_API_KEY=

# App
ENVIRONMENT=development
LOG_LEVEL=INFO
```

Copy it to `.env` for local use:

```bash
cp .env.example .env
```

Then fill in any required values in `.env`.

---

## Step 5: Scaffold Next.js Frontend

```bash
cd apps/web
npx create-next-app@latest . \
  --typescript \
  --tailwind \
  --app \
  --src-dir \
  --import-alias "@/*" \
  --no-git
cd ../..
```

After scaffolding, update `apps/web/next.config.ts`:

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",                          // Required for Docker
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  },
};

export default nextConfig;
```

---

## Step 6: Scaffold FastAPI Backend

```bash
cd apps/api

# Create virtual environment (for local IDE support only — Docker uses its own)
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install \
  fastapi==0.115.0 \
  uvicorn[standard]==0.30.6 \
  pydantic==2.8.0 \
  pydantic-settings==2.4.0 \
  sqlalchemy==2.0.35 \
  alembic==1.13.3 \
  asyncpg==0.29.0 \
  redis==5.1.0 \
  httpx==0.27.2 \
  anthropic==0.34.2 \
  geopandas==1.0.1 \
  shapely==2.0.6 \
  pandas==2.2.3 \
  python-dotenv==1.0.1 \
  python-jose[cryptography]==3.3.0 \
  passlib[bcrypt]==1.7.4 \
  python-multipart==0.0.12

pip freeze > requirements.txt
cd ../..
```

Create `apps/api/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print(f"Starting NeighborhoodIQ API — env: {settings.ENVIRONMENT}")
    yield
    # Shutdown
    print("Shutting down")


app = FastAPI(
    title="NeighborhoodIQ API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "environment": settings.ENVIRONMENT}
```

Create the API package structure:

```bash
mkdir -p apps/api/app/api/v1/endpoints
mkdir -p apps/api/app/core
mkdir -p apps/api/app/models
mkdir -p apps/api/app/schemas
mkdir -p apps/api/app/services
mkdir -p apps/api/app/workers
mkdir -p apps/api/migrations
touch apps/api/app/__init__.py
touch apps/api/app/api/__init__.py
touch apps/api/app/api/v1/__init__.py
touch apps/api/app/api/v1/endpoints/__init__.py
touch apps/api/app/core/__init__.py
touch apps/api/app/models/__init__.py
touch apps/api/app/schemas/__init__.py
touch apps/api/app/services/__init__.py
```

Create `apps/api/app/core/config.py`:

```python
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # Auth
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Claude
    ANTHROPIC_API_KEY: str = ""

    # Mapbox
    MAPBOX_TOKEN: str = ""

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "https://neighborhoodiq.com",
    ]

    # Azure Storage
    AZURE_STORAGE_CONNECTION_STRING: str = ""
    AZURE_STORAGE_CONTAINER_NAME: str = "reports"

    # External APIs
    EPA_AQS_EMAIL: str = ""
    EPA_AQS_KEY: str = ""
    FBI_API_KEY: str = ""
    CENSUS_API_KEY: str = ""

    class Config:
        env_file = "../../.env"
        case_sensitive = True


settings = Settings()
```

Create `apps/api/app/api/v1/router.py`:

```python
from fastapi import APIRouter
from app.api.v1.endpoints import score, lookup, compare, narrative, auth, users

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(lookup.router, prefix="/lookup", tags=["lookup"])
api_router.include_router(score.router, prefix="/score", tags=["score"])
api_router.include_router(compare.router, prefix="/compare", tags=["compare"])
api_router.include_router(narrative.router, prefix="/narrative", tags=["narrative"])
```

---

## Step 7: Scaffold Workers

Create `workers/ingest/requirements.txt`:

```
pandas==2.2.3
geopandas==1.0.1
httpx==0.27.2
sqlalchemy==2.0.35
asyncpg==0.29.0
psycopg2-binary==2.9.9
python-dotenv==1.0.1
tenacity==9.0.0
```

Create `workers/ingest/base.py`:

```python
"""Base class for all ingestion workers."""
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime

from dotenv import load_dotenv

load_dotenv("../../.env")

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
)


class BaseIngestionWorker(ABC):
    def __init__(self, source_name: str):
        self.source_name = source_name
        self.logger = logging.getLogger(source_name)
        self.database_url = os.getenv("DATABASE_URL")

    @abstractmethod
    def fetch(self) -> None:
        """Fetch raw data from source API or file."""
        pass

    @abstractmethod
    def transform(self) -> None:
        """Clean and normalize fetched data."""
        pass

    @abstractmethod
    def load(self) -> None:
        """Write transformed data to PostgreSQL."""
        pass

    def run(self) -> None:
        start = datetime.utcnow()
        self.logger.info(f"Starting {self.source_name} ingestion")
        self.fetch()
        self.transform()
        self.load()
        elapsed = (datetime.utcnow() - start).seconds
        self.logger.info(f"Completed {self.source_name} ingestion in {elapsed}s")
```

---

## Step 8: Root docker-compose.yml

See `docs/04-dockerfiles.md` for Dockerfile contents. Create `docker-compose.yml` at the repo root:

```yaml
services:
  web:
    build:
      context: .
      dockerfile: docker/web.Dockerfile
      target: runner
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
      - NEXTAUTH_SECRET=${NEXTAUTH_SECRET}
      - NEXTAUTH_URL=http://localhost:3000
    depends_on:
      api:
        condition: service_healthy
    restart: unless-stopped

  api:
    build:
      context: .
      dockerfile: docker/api.Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/neighborhoodiq
      - REDIS_URL=redis://redis:6379
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - MAPBOX_TOKEN=${MAPBOX_TOKEN}
      - ENVIRONMENT=development
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
    restart: unless-stopped

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

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data

  worker-epa:
    build:
      context: .
      dockerfile: docker/worker.Dockerfile
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/neighborhoodiq
      - EPA_AQS_EMAIL=${EPA_AQS_EMAIL}
      - EPA_AQS_KEY=${EPA_AQS_KEY}
    command: python -m workers.ingest.epa.run
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

## Step 9: Initial Database Schema

Create `infra/sql/init.sql`:

```sql
-- Enable PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Census tracts (spatial)
CREATE TABLE IF NOT EXISTS census_tracts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    geoid VARCHAR(11) UNIQUE NOT NULL,   -- 11-digit FIPS code
    state_fips VARCHAR(2) NOT NULL,
    county_fips VARCHAR(3) NOT NULL,
    tract_fips VARCHAR(6) NOT NULL,
    geometry GEOMETRY(MULTIPOLYGON, 4326),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_census_tracts_geoid ON census_tracts(geoid);
CREATE INDEX IF NOT EXISTS idx_census_tracts_geometry ON census_tracts USING GIST(geometry);

-- Neighborhood scores (cached per tract)
CREATE TABLE IF NOT EXISTS neighborhood_scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    geoid VARCHAR(11) NOT NULL REFERENCES census_tracts(geoid),
    healthcare_score NUMERIC(4,1),
    safety_score NUMERIC(4,1),
    environment_score NUMERIC(4,1),
    education_score NUMERIC(4,1),
    economic_score NUMERIC(4,1),
    overall_score NUMERIC(4,1),
    data_vintage VARCHAR(10),            -- e.g. "2024-Q3"
    computed_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(geoid, data_vintage)
);

-- Address lookup cache
CREATE TABLE IF NOT EXISTS address_lookups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    address_raw TEXT NOT NULL,
    address_normalized TEXT,
    latitude NUMERIC(10,7),
    longitude NUMERIC(10,7),
    geoid VARCHAR(11),
    lookup_count INTEGER DEFAULT 1,
    first_looked_up_at TIMESTAMPTZ DEFAULT NOW(),
    last_looked_up_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_address_lookups_address ON address_lookups(address_normalized);

-- Users
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password TEXT,
    full_name VARCHAR(255),
    tier VARCHAR(20) DEFAULT 'free',     -- free | buyer | buyer_pro | agent | brokerage
    lookup_count_this_month INTEGER DEFAULT 0,
    billing_cycle_start TIMESTAMPTZ,
    stripe_customer_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Saved lookups per user
CREATE TABLE IF NOT EXISTS saved_lookups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    address_lookup_id UUID NOT NULL REFERENCES address_lookups(id),
    label VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Step 10: Verify Everything Starts

```bash
# From repo root
docker compose up --build

# In another terminal, test the health endpoint
curl http://localhost:8000/health
# Expected: {"status":"ok","environment":"development"}

# Test Next.js
open http://localhost:3000
```

---

## Checklist

- [ ] All directories created
- [ ] `.env.example` committed, `.env` filled in locally
- [ ] Next.js starts at `localhost:3000`
- [ ] FastAPI starts at `localhost:8000`
- [ ] `/health` returns 200
- [ ] PostgreSQL + PostGIS accessible at `localhost:5432`
- [ ] Redis accessible at `localhost:6379`
- [ ] `docker compose up` starts all services cleanly
