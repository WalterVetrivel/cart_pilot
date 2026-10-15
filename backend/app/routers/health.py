from fastapi import APIRouter

from app.auth import AuthUser
from app.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "model": get_settings().gemini_model}


@router.get("/me")
def me(user: AuthUser) -> dict:
    """Echoes the verified Firebase user; handy for checking auth end to end."""
    return {"uid": user.uid, "email": user.email, "name": user.name}
