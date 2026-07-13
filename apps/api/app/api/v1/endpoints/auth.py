from fastapi import APIRouter, Depends

from app.api.deps import get_auth_service
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserPublic
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/register", response_model=UserPublic, status_code=201)
async def register(
    body: RegisterRequest,
    auth: AuthService = Depends(get_auth_service),
) -> UserPublic:
    return await auth.register(
        email=body.email,
        full_name=body.full_name,
        password=body.password,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    auth: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    return await auth.login(email=body.email, password=body.password)
