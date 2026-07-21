from pydantic import BaseModel, EmailStr
from typing import Literal, Optional


UserTier = Literal["free", "buyer", "buyer_pro", "agent", "brokerage"]


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserPublic(BaseModel):
    id: str
    email: str
    full_name: str
    tier: UserTier


class UserInDB(UserPublic):
    password_hash: str
    created_at: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


class SavedLookup(BaseModel):
    user_id: str
    address_id: str
    address_normalized: str
    looked_up_at: str
    last_activity_at: str
    is_favorite: bool = False
    overall_score: Optional[float] = None


class LookupListResponse(BaseModel):
    items: list[SavedLookup]


class SavedLookupFavoriteUpdate(BaseModel):
    is_favorite: bool


class SavedLookupTouchResponse(BaseModel):
    item: SavedLookup
