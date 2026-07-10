from pydantic import BaseModel, EmailStr
from typing import Literal


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


class LookupListResponse(BaseModel):
    items: list[SavedLookup]
