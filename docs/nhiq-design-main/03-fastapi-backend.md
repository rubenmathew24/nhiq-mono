# 03 — FastAPI Backend

> **Claude instructions:** All backend code lives in `apps/api/`. Follow the layered architecture strictly: routes call services, services call repositories or external clients. No database queries in route handlers.

---

## Architecture Layers

```
Route Handler  →  Service  →  Repository (DB)
                           →  External API Client
                           →  Redis Cache
                           →  Claude AI Client
```

---

## Full Directory Structure

```
apps/api/
├── main.py                          # FastAPI app entry point
├── requirements.txt
├── alembic.ini                      # DB migrations config
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── router.py            # Combines all endpoint routers
│   │       └── endpoints/
│   │           ├── auth.py
│   │           ├── users.py
│   │           ├── lookup.py        # Address geocoding + tract lookup
│   │           ├── score.py         # Score retrieval
│   │           ├── compare.py       # Side-by-side comparison
│   │           └── narrative.py     # AI narrative generation
│   ├── core/
│   │   ├── config.py                # Settings (pydantic-settings)
│   │   ├── database.py              # SQLAlchemy async engine
│   │   ├── redis.py                 # Redis client
│   │   ├── security.py              # JWT, password hashing
│   │   └── dependencies.py         # FastAPI Depends() helpers
│   ├── models/
│   │   ├── user.py                  # SQLAlchemy ORM models
│   │   ├── score.py
│   │   └── address.py
│   ├── schemas/
│   │   ├── user.py                  # Pydantic request/response models
│   │   ├── score.py
│   │   ├── address.py
│   │   └── narrative.py
│   ├── services/
│   │   ├── geocoding.py             # Address → lat/lng → census tract
│   │   ├── scoring.py               # Aggregate scores from raw data
│   │   ├── narrative.py             # Claude API integration
│   │   ├── cache.py                 # Redis get/set helpers
│   │   └── users.py                 # User CRUD
│   └── clients/
│       ├── cms.py                   # CMS API client
│       ├── epa.py                   # EPA API client
│       ├── fema.py                  # FEMA data client
│       ├── fbi.py                   # FBI Crime Data client
│       ├── census.py                # Census Bureau client
│       └── mapbox.py                # Mapbox Geocoding client
└── migrations/
    └── versions/                    # Alembic migration files
```

---

## Step 1: Database Setup (`app/core/database.py`)

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# Convert postgresql:// to postgresql+asyncpg://
db_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(
    db_url,
    echo=settings.ENVIRONMENT == "development",
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

---

## Step 2: Redis Client (`app/core/redis.py`)

```python
import redis.asyncio as aioredis
from app.core.config import settings

redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global redis_client
    if redis_client is None:
        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return redis_client
```

---

## Step 3: Security (`app/core/security.py`)

```python
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    expire = datetime.utcnow() + (expires_delta or timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    ))
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> str:
    """Returns user_id (sub) or raises JWTError."""
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    return payload["sub"]
```

---

## Step 4: Dependencies (`app/core/dependencies.py`)

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError

from app.core.database import get_db
from app.core.security import decode_token
from app.services.users import get_user_by_id
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        user_id = decode_token(token)
    except JWTError:
        raise credentials_exception

    user = await get_user_by_id(db, user_id)
    if user is None:
        raise credentials_exception
    return user


async def require_paid_tier(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.tier == "free":
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="This feature requires a paid plan",
        )
    return current_user
```

---

## Step 5: ORM Models (`app/models/`)

`app/models/user.py`:
```python
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
import uuid
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String)
    full_name: Mapped[str | None] = mapped_column(String(255))
    tier: Mapped[str] = mapped_column(String(20), default="free")
    lookup_count_this_month: Mapped[int] = mapped_column(Integer, default=0)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

`app/models/score.py`:
```python
from sqlalchemy import String, Numeric, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
import uuid
from app.core.database import Base


class NeighborhoodScore(Base):
    __tablename__ = "neighborhood_scores"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    geoid: Mapped[str] = mapped_column(String(11), nullable=False)
    healthcare_score: Mapped[float | None] = mapped_column(Numeric(4, 1))
    safety_score: Mapped[float | None] = mapped_column(Numeric(4, 1))
    environment_score: Mapped[float | None] = mapped_column(Numeric(4, 1))
    education_score: Mapped[float | None] = mapped_column(Numeric(4, 1))
    economic_score: Mapped[float | None] = mapped_column(Numeric(4, 1))
    overall_score: Mapped[float | None] = mapped_column(Numeric(4, 1))
    data_vintage: Mapped[str | None] = mapped_column(String(10))
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

---

## Step 6: Pydantic Schemas (`app/schemas/score.py`)

```python
from pydantic import BaseModel
from typing import Literal
from datetime import datetime


class Factor(BaseModel):
    name: str
    value: str
    impact: Literal["positive", "negative", "neutral"]


class ScoreDimension(BaseModel):
    score: float
    label: str
    summary: str
    factors: list[Factor]


class NeighborhoodReport(BaseModel):
    address: str
    address_normalized: str
    geoid: str
    latitude: float
    longitude: float
    overall_score: float
    healthcare: ScoreDimension
    safety: ScoreDimension
    environment: ScoreDimension
    education: ScoreDimension
    economic: ScoreDimension
    narrative: str | None = None     # None for free tier
    data_vintage: str
    computed_at: datetime


class LookupResponse(BaseModel):
    address_id: str
    status: Literal["cached", "computing", "ready"]
    report: NeighborhoodReport | None = None


class CompareReport(BaseModel):
    address_a: NeighborhoodReport
    address_b: NeighborhoodReport
    ai_commentary: str | None = None  # Buyer tier+
```

---

## Step 7: Geocoding Service (`app/services/geocoding.py`)

```python
import httpx
from app.core.config import settings


async def geocode_address(address: str) -> dict:
    """
    Returns {lat, lng, normalized_address} using Mapbox Geocoding API.
    Raises ValueError if address cannot be geocoded.
    """
    url = "https://api.mapbox.com/geocoding/v5/mapbox.places/" + \
          f"{httpx.URL(address)}.json"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params={
            "access_token": settings.MAPBOX_TOKEN,
            "country": "US",
            "types": "address",
            "limit": 1,
        })
        response.raise_for_status()
        data = response.json()

    if not data["features"]:
        raise ValueError(f"Could not geocode address: {address}")

    feature = data["features"][0]
    lng, lat = feature["center"]

    return {
        "latitude": lat,
        "longitude": lng,
        "address_normalized": feature["place_name"],
    }


async def get_census_tract(lat: float, lng: float) -> str:
    """
    Returns 11-digit census tract GEOID using Census Geocoder API.
    Free, no key required.
    """
    url = "https://geocoding.geo.census.gov/geocoder/geographies/coordinates"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params={
            "x": lng,
            "y": lat,
            "benchmark": "Public_AR_Current",
            "vintage": "Current_Current",
            "format": "json",
        })
        response.raise_for_status()
        data = response.json()

    try:
        tract = data["result"]["geographies"]["Census Tracts"][0]
        state = tract["STATE"]
        county = tract["COUNTY"]
        tract_code = tract["TRACT"]
        return f"{state}{county}{tract_code}"   # 11-digit GEOID
    except (KeyError, IndexError):
        raise ValueError(f"Could not find census tract for ({lat}, {lng})")
```

---

## Step 8: Claude Narrative Service (`app/services/narrative.py`)

```python
import anthropic
from app.core.config import settings
from app.schemas.score import NeighborhoodReport

client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)


async def generate_narrative(report: NeighborhoodReport, user_profile: str = "general") -> str:
    """
    Generates a 3-4 paragraph plain-English neighborhood narrative using Claude.
    user_profile: "general" | "family" | "retiree" | "young_professional"
    """
    profile_context = {
        "general": "a general home buyer",
        "family": "a family with children considering schools, safety, and nearby parks",
        "retiree": "a retiree prioritizing healthcare access, walkability, and low crime",
        "young_professional": "a young professional prioritizing walkability, amenities, and economic vitality",
    }

    prompt = f"""You are a neighborhood analyst helping {profile_context.get(user_profile, "a home buyer")} evaluate a potential home address.

Here is the neighborhood data for {report.address_normalized}:

Overall Score: {report.overall_score}/100
- Healthcare Access: {report.healthcare.score}/100 — {report.healthcare.summary}
- Safety & Environment: {report.safety.score}/100 — {report.safety.summary}
- Education & Amenities: {report.education.score}/100 — {report.education.summary}
- Economic Health: {report.economic.score}/100 — {report.economic.summary}

Write a 3-paragraph plain-English neighborhood assessment. Rules:
1. Be specific — use the scores and summaries, not vague generalities
2. Lead with the most important insight for this buyer profile
3. Mention 1-2 trade-offs honestly
4. End with a bottom-line recommendation sentence
5. Do NOT use bullet points — flowing prose only
6. Do NOT repeat the scores numerically — translate them into plain language
7. Tone: warm, informative, like a knowledgeable friend who knows the neighborhood
"""

    message = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text


async def generate_comparison_commentary(
    report_a: NeighborhoodReport,
    report_b: NeighborhoodReport,
) -> str:
    """Generates AI trade-off commentary for side-by-side comparison."""

    prompt = f"""Compare these two neighborhoods for a home buyer:

Address A: {report_a.address_normalized}
- Overall: {report_a.overall_score}/100
- Healthcare: {report_a.healthcare.score} | Safety: {report_a.safety.score} | Education: {report_a.education.score} | Economic: {report_a.economic.score}

Address B: {report_b.address_normalized}
- Overall: {report_b.overall_score}/100
- Healthcare: {report_b.healthcare.score} | Safety: {report_b.safety.score} | Education: {report_b.education.score} | Economic: {report_b.economic.score}

Write 2 paragraphs:
1. What Address A does better and who it's right for
2. What Address B does better and who it's right for

Be specific, honest about trade-offs, and concise. No bullet points.
"""

    message = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text
```

---

## Step 9: Endpoint — Lookup (`app/api/v1/endpoints/lookup.py`)

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.score import LookupResponse
from app.services.geocoding import geocode_address, get_census_tract
from app.services.cache import get_cached_score

router = APIRouter()


@router.get("", response_model=LookupResponse)
async def lookup_address(
    address: str,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user),
):
    """
    Geocode an address, find its census tract, and return cached score if available.
    Free tier: max 3 lookups/month. Returns address_id for polling /score/{address_id}.
    """
    # Enforce free tier limit
    if current_user and current_user.tier == "free":
        if current_user.lookup_count_this_month >= 3:
            raise HTTPException(
                status_code=402,
                detail="Free tier limit reached. Upgrade for unlimited lookups.",
            )

    try:
        geo = await geocode_address(address)
        geoid = await get_census_tract(geo["latitude"], geo["longitude"])
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    address_id = str(uuid.uuid4())
    cached = await get_cached_score(geoid)

    return LookupResponse(
        address_id=address_id,
        status="cached" if cached else "computing",
        report=cached,
    )
```

---

## Step 10: Cache Service (`app/services/cache.py`)

```python
import json
from app.core.redis import get_redis
from app.schemas.score import NeighborhoodReport

SCORE_TTL = 60 * 60 * 24       # 24 hours
NARRATIVE_TTL = 60 * 60 * 6    # 6 hours


async def get_cached_score(geoid: str) -> NeighborhoodReport | None:
    redis = await get_redis()
    cached = await redis.get(f"score:{geoid}")
    if cached:
        return NeighborhoodReport.model_validate_json(cached)
    return None


async def set_cached_score(geoid: str, report: NeighborhoodReport) -> None:
    redis = await get_redis()
    await redis.setex(
        f"score:{geoid}",
        SCORE_TTL,
        report.model_dump_json(),
    )


async def get_cached_narrative(geoid: str, profile: str) -> str | None:
    redis = await get_redis()
    return await redis.get(f"narrative:{geoid}:{profile}")


async def set_cached_narrative(geoid: str, profile: str, text: str) -> None:
    redis = await get_redis()
    await redis.setex(f"narrative:{geoid}:{profile}", NARRATIVE_TTL, text)
```

---

## Step 11: Alembic Migration Setup

```bash
cd apps/api
alembic init migrations
```

Update `alembic.ini`:
```ini
sqlalchemy.url = postgresql://postgres:postgres@localhost:5432/neighborhoodiq
```

Update `migrations/env.py` to use async engine and import all models before running migrations. See Alembic async docs.

Generate first migration:
```bash
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

---

## Running the API Locally

```bash
cd apps/api
source .venv/bin/activate

# With hot reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run migrations
alembic upgrade head
```

API docs available at: `http://localhost:8000/api/docs`

---

## Checklist

- [ ] All directories and `__init__.py` files created
- [ ] `GET /health` returns 200
- [ ] API docs render at `/api/docs`
- [ ] Database connection works (check startup logs)
- [ ] Redis connection works
- [ ] `POST /api/v1/auth/register` creates a user
- [ ] `POST /api/v1/auth/login` returns JWT
- [ ] `GET /api/v1/lookup?address=...` geocodes and returns tract
- [ ] Alembic migrations run cleanly
