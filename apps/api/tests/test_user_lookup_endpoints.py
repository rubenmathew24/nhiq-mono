"""HTTP tests for /api/v1/users/me/lookups* (LookupStore mocked)."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_lookup_store
from app.core.security import create_access_token
from app.schemas.auth import SavedLookup
from main import app


def _item(**kwargs) -> SavedLookup:
    base = dict(
        user_id="user-1",
        address_id="addr-1",
        address_normalized="1 Main St",
        looked_up_at="2026-07-01T00:00:00+00:00",
        last_activity_at="2026-07-01T00:00:00+00:00",
        is_favorite=False,
        overall_score=70.0,
    )
    base.update(kwargs)
    return SavedLookup(**base)


@pytest.fixture()
def mock_store():
    mock = MagicMock()
    mock.list_for_user = AsyncMock(return_value=[])
    mock.set_favorite = AsyncMock()
    mock.delete_for_user = AsyncMock()
    mock.touch = AsyncMock()
    app.dependency_overrides[get_lookup_store] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_lookup_store, None)


@pytest.fixture()
def client(mock_store):
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth_headers():
    token = create_access_token("user-1")
    return {"Authorization": f"Bearer {token}"}


def test_patch_favorite(client, mock_store, auth_headers):
    mock_store.set_favorite.return_value = _item(is_favorite=True)
    resp = client.patch(
        "/api/v1/users/me/lookups/addr-1",
        headers=auth_headers,
        json={"is_favorite": True},
    )
    assert resp.status_code == 200
    assert resp.json()["is_favorite"] is True
    mock_store.set_favorite.assert_awaited_once_with(
        "user-1", "addr-1", is_favorite=True
    )


def test_delete_returns_204(client, mock_store, auth_headers):
    mock_store.delete_for_user.return_value = "deleted"
    resp = client.delete("/api/v1/users/me/lookups/addr-1", headers=auth_headers)
    assert resp.status_code == 204
    assert resp.content == b""


def test_delete_favorited_returns_409(client, mock_store, auth_headers):
    mock_store.delete_for_user.return_value = "favorited"
    resp = client.delete("/api/v1/users/me/lookups/addr-1", headers=auth_headers)
    assert resp.status_code == 409
    assert "Unfavorite" in resp.json()["detail"]


def test_touch_updates_activity(client, mock_store, auth_headers):
    mock_store.touch.return_value = _item(
        last_activity_at="2026-07-21T12:00:00+00:00"
    )
    resp = client.post(
        "/api/v1/users/me/lookups/addr-1/touch",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["last_activity_at"].startswith("2026-07-21")
    mock_store.touch.assert_awaited_once_with("user-1", "addr-1")
