from typing import Optional

from fastapi import HTTPException, status

from app.core.security import create_access_token, hash_password, verify_password
from app.schemas.auth import TokenResponse, UserInDB, UserPublic
from app.services.user_store import UserStore, user_store as _default_store


class AuthService:
    def __init__(self, store: Optional[UserStore] = None) -> None:
        self._store = store or _default_store

    def register(self, email: str, full_name: str, password: str) -> UserPublic:
        if self._store.get_by_email(email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists. Please sign in instead.",
            )
        hashed = hash_password(password)
        user = self._store.create(email=email, full_name=full_name, password_hash=hashed)
        return UserPublic(id=user.id, email=user.email, full_name=user.full_name, tier=user.tier)

    def login(self, email: str, password: str) -> TokenResponse:
        user = self._store.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token = create_access_token(subject=user.id)
        public = UserPublic(id=user.id, email=user.email, full_name=user.full_name, tier=user.tier)
        return TokenResponse(access_token=token, user=public)

    def get_user_by_id(self, user_id: str) -> UserPublic:
        user = self._store.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
        return UserPublic(id=user.id, email=user.email, full_name=user.full_name, tier=user.tier)


auth_service = AuthService()
