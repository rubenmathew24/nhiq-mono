from fastapi import APIRouter

from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserPublic
from app.services.auth_service import auth_service

router = APIRouter()


@router.post("/register", response_model=UserPublic, status_code=201)
def register(body: RegisterRequest) -> UserPublic:
    return auth_service.register(
        email=body.email,
        full_name=body.full_name,
        password=body.password,
    )


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest) -> TokenResponse:
    return auth_service.login(email=body.email, password=body.password)
