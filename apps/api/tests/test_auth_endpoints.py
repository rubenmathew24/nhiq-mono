"""Tests for /api/v1/auth/* endpoints using the TEMP file store.

TEMPORARY: Update to use DB fixtures when Postgres auth lands.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from main import app
from app.services.auth_service import AuthService, auth_service
from app.schemas.auth import UserPublic, TokenResponse


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def mock_auth_service(monkeypatch):
    mock = MagicMock(spec=AuthService)
    monkeypatch.setattr("app.api.v1.endpoints.auth.auth_service", mock)
    monkeypatch.setattr("app.api.v1.endpoints.users.auth_service", mock)
    return mock


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
    from fastapi import HTTPException
    mock_auth_service.register.side_effect = HTTPException(
        status_code=409, detail="An account with this email already exists."
    )
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "dup@example.com", "password": "pw", "full_name": "Dup"},
    )
    assert resp.status_code == 409


def test_login_success(client, mock_auth_service):
    mock_auth_service.login.return_value = TokenResponse(
        access_token="tok123",
        user=UserPublic(id="abc", email="a@b.com", full_name="Alice", tier="free"),
    )
    resp = client.post("/api/v1/auth/login", json={"email": "a@b.com", "password": "pw"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_bad_credentials_returns_401(client, mock_auth_service):
    from fastapi import HTTPException
    mock_auth_service.login.side_effect = HTTPException(
        status_code=401, detail="Invalid email or password."
    )
    resp = client.post("/api/v1/auth/login", json={"email": "a@b.com", "password": "wrong"})
    assert resp.status_code == 401
