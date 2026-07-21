from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.deps import get_auth_service, get_lookup_store
from app.core.security import decode_access_token
from app.schemas.auth import (
    LookupListResponse,
    SavedLookup,
    SavedLookupFavoriteUpdate,
    UserPublic,
)
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


@router.patch("/me/lookups/{address_id}", response_model=SavedLookup)
async def update_my_lookup(
    address_id: str,
    body: SavedLookupFavoriteUpdate,
    user_id: str = Depends(get_current_user_id),
    store: LookupStore = Depends(get_lookup_store),
) -> SavedLookup:
    item = await store.set_favorite(
        user_id, address_id, is_favorite=body.is_favorite
    )
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved lookup not found.",
        )
    return item


@router.delete("/me/lookups/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_lookup(
    address_id: str,
    user_id: str = Depends(get_current_user_id),
    store: LookupStore = Depends(get_lookup_store),
) -> Response:
    result = await store.delete_for_user(user_id, address_id)
    if result == "not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved lookup not found.",
        )
    if result == "favorited":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unfavorite this address before deleting it.",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/me/lookups/{address_id}/touch", response_model=SavedLookup)
async def touch_my_lookup(
    address_id: str,
    user_id: str = Depends(get_current_user_id),
    store: LookupStore = Depends(get_lookup_store),
) -> SavedLookup:
    item = await store.touch(user_id, address_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved lookup not found.",
        )
    return item
