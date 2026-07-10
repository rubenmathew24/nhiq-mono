from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_access_token
from app.schemas.auth import LookupListResponse, UserPublic
from app.services.auth_service import auth_service
from app.services.lookup_store import lookup_store

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
def get_me(user_id: str = Depends(get_current_user_id)) -> UserPublic:
    return auth_service.get_user_by_id(user_id)


@router.get("/me/lookups", response_model=LookupListResponse)
def get_my_lookups(user_id: str = Depends(get_current_user_id)) -> LookupListResponse:
    items = lookup_store.list_for_user(user_id)
    return LookupListResponse(items=items)
