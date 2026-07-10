# TEMPORARY: File-backed user store for UI development only.
# DELETE when Postgres users table is implemented.
# See specs/001-web-app-pages/research.md removal checklist.

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Protocol, runtime_checkable

from app.schemas.auth import UserInDB


# apps/api/app/services/user_store.py → parents[2] == apps/api
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
USERS_FILE = DATA_DIR / "TEMP_dev_users.jsonl"


@runtime_checkable
class UserStore(Protocol):
    def get_by_email(self, email: str) -> Optional[UserInDB]: ...
    def get_by_id(self, user_id: str) -> Optional[UserInDB]: ...
    def create(self, email: str, full_name: str, password_hash: str) -> UserInDB: ...


class FileUserStore:
    """TEMPORARY file-backed implementation. Replace with Postgres repository."""

    def _read_all(self) -> list[UserInDB]:
        if not USERS_FILE.exists():
            return []
        users: list[UserInDB] = []
        with USERS_FILE.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    users.append(UserInDB(**json.loads(line)))
        return users

    def _append(self, user: UserInDB) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with USERS_FILE.open("a", encoding="utf-8") as f:
            f.write(user.model_dump_json() + "\n")

    def get_by_email(self, email: str) -> Optional[UserInDB]:
        for user in self._read_all():
            if user.email.lower() == email.lower():
                return user
        return None

    def get_by_id(self, user_id: str) -> Optional[UserInDB]:
        for user in self._read_all():
            if user.id == user_id:
                return user
        return None

    def create(self, email: str, full_name: str, password_hash: str) -> UserInDB:
        user = UserInDB(
            id=str(uuid.uuid4()),
            email=email,
            full_name=full_name,
            password_hash=password_hash,
            tier="free",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._append(user)
        return user


# Singleton used by services — swap this for a DB-backed implementation.
user_store: UserStore = FileUserStore()
