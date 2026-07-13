"""Tests for /api/v1/auth/* endpoints (AuthService mocked via DI)."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.deps import get_auth_service
from app.schemas.auth import TokenResponse, UserPublic
from app.services.auth_service import AuthService
from main import app


@pytest.fixture()
def mock_auth_service():
    mock = MagicMock(spec=AuthService)
    mock.register = AsyncMock()
    mock.login = AsyncMock()
    mock.get_user_by_id = AsyncMock()
    app.dependency_overrides[get_auth_service] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_auth_service, None)


@pytest.fixture()
def client(mock_auth_service):
    with TestClient(app) as c:
        yield c


def test_register_success(client, mock_auth_service):
    mock_auth_service.register.return_value = UserPublic(
        id="abc", email="new@example.com", full_name="New User", tier="free"
    )
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "password": "password123", "full_name": "New User"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "new@example.com"
    assert data["tier"] == "free"


def test_register_duplicate_email_returns_409(client, mock_auth_service):
    mock_auth_service.register.side_effect = HTTPException(
        status_code=409, detail="An account with this email already exists."
    )
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "dup@example.com", "password": "password123", "full_name": "Dup"},
    )
    assert resp.status_code == 409


def test_login_success(client, mock_auth_service):
    mock_auth_service.login.return_value = TokenResponse(
        access_token="tok123",
        user=UserPublic(id="abc", email="a@b.com", full_name="Alice", tier="free"),
    )
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "a@b.com", "password": "password123"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_bad_credentials_returns_401(client, mock_auth_service):
    mock_auth_service.login.side_effect = HTTPException(
        status_code=401, detail="Invalid email or password."
    )
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "a@b.com", "password": "wrongpassword"},
    )
    assert resp.status_code == 401
