# 09 — Testing

> **Claude instructions:** Write tests alongside features — not after. Backend tests go in `apps/api/tests/`. Frontend tests go in `apps/web/src/__tests__/`. Run the full test suite before committing to `main`.

---

## Backend Testing (FastAPI + pytest)

### Install test dependencies

```bash
cd apps/api
pip install pytest pytest-asyncio httpx factory-boy pytest-cov
```

Add to `requirements.txt`:
```
pytest==8.3.3
pytest-asyncio==0.24.0
httpx==0.27.2
factory-boy==3.3.1
pytest-cov==5.0.0
```

### `apps/api/pytest.ini`

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
env =
    ENVIRONMENT=test
    DATABASE_URL=postgresql://postgres:postgres@localhost:5432/neighborhoodiq_test
    REDIS_URL=redis://localhost:6379
    ANTHROPIC_API_KEY=test-not-real
    MAPBOX_TOKEN=test-not-real
    SECRET_KEY=test-secret-key-do-not-use-in-prod
```

### `apps/api/tests/conftest.py`

```python
import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from main import app
from app.core.database import Base, get_db
from app.core.config import settings

# Test DB engine
TEST_DB_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session")
async def setup_database():
    """Create all tables once per test session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(setup_database):
    """Fresh DB session per test, rolled back after."""
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session):
    """Test HTTP client with DB override."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_client(client, db_session):
    """Authenticated test client (creates a test user and returns token)."""
    # Register
    await client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "TestPassword123!",
        "full_name": "Test User",
    })

    # Login
    response = await client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "TestPassword123!",
    })
    token = response.json()["access_token"]

    client.headers.update({"Authorization": f"Bearer {token}"})
    return client
```

### `apps/api/tests/test_health.py`

```python
import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

### `apps/api/tests/test_auth.py`

```python
import pytest


@pytest.mark.asyncio
async def test_register_new_user(client):
    response = await client.post("/api/v1/auth/register", json={
        "email": "newuser@example.com",
        "password": "StrongPassword123!",
        "full_name": "New User",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["tier"] == "free"
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email_fails(client):
    payload = {"email": "dup@example.com", "password": "Pass123!", "full_name": "User"}
    await client.post("/api/v1/auth/register", json=payload)
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_returns_token(client):
    await client.post("/api/v1/auth/register", json={
        "email": "login@example.com",
        "password": "Pass123!",
        "full_name": "Login User",
    })
    response = await client.post("/api/v1/auth/login", json={
        "email": "login@example.com",
        "password": "Pass123!",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password_fails(client):
    await client.post("/api/v1/auth/register", json={
        "email": "bad@example.com",
        "password": "CorrectPass!",
        "full_name": "User",
    })
    response = await client.post("/api/v1/auth/login", json={
        "email": "bad@example.com",
        "password": "WrongPass!",
    })
    assert response.status_code == 401
```

### `apps/api/tests/test_lookup.py`

```python
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_lookup_unauthenticated_allowed(client):
    """Free anonymous lookup should work (up to limit)."""
    with patch("app.api.v1.endpoints.lookup.geocode_address") as mock_geo, \
         patch("app.api.v1.endpoints.lookup.get_census_tract") as mock_tract:

        mock_geo.return_value = {
            "latitude": 34.0522,
            "longitude": -118.2437,
            "address_normalized": "123 Main St, Los Angeles, CA 90012",
        }
        mock_tract.return_value = "06037201400"

        response = await client.get("/api/v1/lookup?address=123+Main+St+Los+Angeles+CA")
        assert response.status_code == 200
        data = response.json()
        assert "address_id" in data
        assert data["status"] in ("cached", "computing")


@pytest.mark.asyncio
async def test_lookup_free_tier_limit(auth_client):
    """Free users max out at 3 lookups per month."""
    with patch("app.api.v1.endpoints.lookup.geocode_address") as mock_geo, \
         patch("app.api.v1.endpoints.lookup.get_census_tract") as mock_tract:

        mock_geo.return_value = {
            "latitude": 34.0522,
            "longitude": -118.2437,
            "address_normalized": "123 Main St, Los Angeles, CA 90012",
        }
        mock_tract.return_value = "06037201400"

        # First 3 should succeed
        for _ in range(3):
            r = await auth_client.get("/api/v1/lookup?address=123+Main+St")
            assert r.status_code == 200

        # 4th should fail
        r = await auth_client.get("/api/v1/lookup?address=456+Oak+Ave")
        assert r.status_code == 402


@pytest.mark.asyncio
async def test_lookup_invalid_address(client):
    with patch("app.api.v1.endpoints.lookup.geocode_address") as mock_geo:
        mock_geo.side_effect = ValueError("Could not geocode address")
        response = await client.get("/api/v1/lookup?address=zzz+not+a+real+address")
        assert response.status_code == 422
```

### `apps/api/tests/test_scoring.py`

```python
import pytest
from app.services.scoring import compute_healthcare_score


@pytest.mark.asyncio
async def test_healthcare_score_range(db_session):
    """Score should always be 0-100."""
    score = await compute_healthcare_score(db_session, "06037201400")
    assert 0 <= score <= 100


@pytest.mark.asyncio
async def test_healthcare_score_returns_default_when_no_data(db_session):
    """Tracts with no hospital data should get a neutral default."""
    score = await compute_healthcare_score(db_session, "99999999999")
    assert score == 50.0


def test_score_weights_sum_to_one():
    from app.services.scoring import SCORE_WEIGHTS
    assert abs(sum(SCORE_WEIGHTS.values()) - 1.0) < 0.001
```

### `apps/api/tests/test_narrative.py`

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.narrative import generate_narrative
from app.schemas.score import NeighborhoodReport, ScoreDimension


def make_mock_report():
    dim = ScoreDimension(score=75, label="Test", summary="Test summary", factors=[])
    return NeighborhoodReport(
        address="123 Main St",
        address_normalized="123 Main St, Los Angeles, CA 90012",
        geoid="06037201400",
        latitude=34.0522,
        longitude=-118.2437,
        overall_score=72.5,
        healthcare=dim,
        safety=dim,
        environment=dim,
        education=dim,
        economic=dim,
        data_vintage="2024-Q4",
        computed_at="2024-01-01T00:00:00Z",
    )


@pytest.mark.asyncio
async def test_narrative_returns_string(monkeypatch):
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="This is a test narrative about the neighborhood.")]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_message)

    with patch("app.services.narrative.client", mock_client):
        result = await generate_narrative(make_mock_report(), "general")
        assert isinstance(result, str)
        assert len(result) > 10
```

---

## Frontend Testing (Next.js + Vitest)

### Install

```bash
cd apps/web
npm install -D vitest @testing-library/react @testing-library/user-event @vitejs/plugin-react jsdom
```

### `apps/web/vitest.config.ts`

```typescript
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/__tests__/setup.ts",
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
```

### `apps/web/src/__tests__/setup.ts`

```typescript
import "@testing-library/jest-dom";
```

### `apps/web/src/__tests__/utils.test.ts`

```typescript
import { describe, it, expect } from "vitest";
import { scoreColor, scoreGrade, cn } from "@/lib/utils";

describe("scoreColor", () => {
  it("returns green for scores >= 75", () => {
    expect(scoreColor(75)).toBe("text-green-400");
    expect(scoreColor(100)).toBe("text-green-400");
  });

  it("returns yellow for scores 50-74", () => {
    expect(scoreColor(50)).toBe("text-yellow-400");
    expect(scoreColor(74)).toBe("text-yellow-400");
  });

  it("returns red for scores < 50", () => {
    expect(scoreColor(0)).toBe("text-red-400");
    expect(scoreColor(49)).toBe("text-red-400");
  });
});

describe("scoreGrade", () => {
  it("returns A+ for >= 90", () => expect(scoreGrade(90)).toBe("A+"));
  it("returns F for < 50", () => expect(scoreGrade(30)).toBe("F"));
});
```

### `apps/web/src/__tests__/AddressSearch.test.tsx`

```typescript
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import AddressSearch from "@/components/search/AddressSearch";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

// Mock the API client
vi.mock("@/lib/api", () => ({
  apiFetch: vi.fn().mockResolvedValue({
    address_id: "test-id-123",
    status: "cached",
  }),
}));

describe("AddressSearch", () => {
  it("renders the search input and button", () => {
    render(<AddressSearch />);
    expect(screen.getByPlaceholderText(/Enter any U.S. address/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Analyze/i })).toBeInTheDocument();
  });

  it("disables button when input is empty", () => {
    render(<AddressSearch />);
    expect(screen.getByRole("button", { name: /Analyze/i })).toBeDisabled();
  });

  it("enables button when address is typed", async () => {
    render(<AddressSearch />);
    const input = screen.getByPlaceholderText(/Enter any U.S. address/i);
    fireEvent.change(input, { target: { value: "123 Main St" } });
    expect(screen.getByRole("button", { name: /Analyze/i })).not.toBeDisabled();
  });
});
```

---

## Running Tests

```bash
# Backend
cd apps/api
pytest tests/ -v                          # All tests
pytest tests/ -v --cov=app --cov-report=html  # With coverage
pytest tests/test_auth.py -v              # Single file
pytest tests/ -k "lookup" -v             # By keyword

# Frontend
cd apps/web
npm run test                              # Watch mode
npm run test -- --run                    # Single run (CI)
npm run test -- --coverage               # With coverage
```

---

## What to Mock vs What to Test with Real DB

| Scenario | Approach |
|---|---|
| External APIs (Mapbox, Claude, EPA) | Always mock with `unittest.mock.patch` |
| Database queries | Use real test DB (fast PostgreSQL in Docker) |
| Redis | Use real Redis or `fakeredis` |
| Auth token generation/validation | Test against real JWT logic |
| Score computation | Test with real DB, seed minimal fixture data |

---

## Checklist

- [ ] `pytest.ini` configured
- [ ] `conftest.py` with client and auth fixtures
- [ ] Health check test passes
- [ ] Auth register/login/duplicate tests pass
- [ ] Lookup free-tier limit test passes
- [ ] Narrative mock test passes
- [ ] Frontend utility tests pass
- [ ] AddressSearch component test passes
- [ ] CI runs all tests on every PR (see `docs/05-cicd.md`)
- [ ] Coverage report generated (aim for > 70% on `app/`)
