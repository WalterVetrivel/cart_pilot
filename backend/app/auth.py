"""Firebase ID token verification (SPEC §9: every endpoint except /health)."""

from dataclasses import dataclass
from typing import Annotated

import firebase_admin
from fastapi import Depends, Header
from firebase_admin import auth as fb_auth

from app.config import Settings, get_settings
from app.errors import ApiError


@dataclass(frozen=True)
class CurrentUser:
    uid: str
    email: str | None = None
    name: str | None = None


def _ensure_firebase_app(settings: Settings) -> None:
    if not firebase_admin._apps:
        options = {"projectId": settings.google_cloud_project} if settings.google_cloud_project else None
        firebase_admin.initialize_app(options=options)


def get_current_user(
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
) -> CurrentUser:
    if settings.auth_disabled:
        return CurrentUser(uid="dev-user", email="dev@example.com", name="Dev User")

    if not authorization or not authorization.startswith("Bearer "):
        raise ApiError(401, "unauthenticated", "Missing Bearer token.")

    _ensure_firebase_app(settings)
    try:
        claims = fb_auth.verify_id_token(authorization.removeprefix("Bearer "))
    except Exception as exc:  # firebase raises several token error types
        raise ApiError(401, "invalid_token", "Invalid or expired ID token.") from exc

    return CurrentUser(uid=claims["uid"], email=claims.get("email"), name=claims.get("name"))


AuthUser = Annotated[CurrentUser, Depends(get_current_user)]
