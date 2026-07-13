from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.deps import get_auth_service, get_lookup_store
from app.core.security import decode_access_token
from app.schemas.auth import LookupListResponse, UserPublic
from app.services.auth_service import AuthService
from app.services.lookup_store import LookupStore

router = APIRouter()
bearer = HTTPBearer()


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> str:
    user_id = decode_access_token(credentials.credentials)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id


@router.get("/me", response_model=UserPublic)
async def get_me(
    user_id: str = Depends(get_current_user_id),
    auth: AuthService = Depends(get_auth_service),
) -> UserPublic:
    return await auth.get_user_by_id(user_id)


@router.get("/me/lookups", response_model=LookupListResponse)
async def get_my_lookups(
    user_id: str = Depends(get_current_user_id),
    store: LookupStore = Depends(get_lookup_store),
) -> LookupListResponse:
    items = await store.list_for_user(user_id)
    return LookupListResponse(items=items)
