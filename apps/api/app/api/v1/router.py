from fastapi import APIRouter
from app.api.v1.endpoints import (
    score,
    lookup,
    compare,
    narrative,
    auth,
    users,
    coverage,
    discover,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(lookup.router, prefix="/lookup", tags=["lookup"])
api_router.include_router(score.router, prefix="/score", tags=["score"])
api_router.include_router(compare.router, prefix="/compare", tags=["compare"])
api_router.include_router(narrative.router, prefix="/narrative", tags=["narrative"])
api_router.include_router(coverage.router, prefix="/coverage", tags=["coverage"])
api_router.include_router(discover.router, prefix="/discover", tags=["discover"])
