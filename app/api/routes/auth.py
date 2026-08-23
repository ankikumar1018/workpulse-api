"""Authentication endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import AuthCtrl
from app.api.utils import make_success_response
from app.schemas import RefreshTokenRequest, SuccessEnvelope

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/token", response_model=SuccessEnvelope, status_code=status.HTTP_200_OK)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    controller: AuthCtrl,
):
    """Authenticate with email in the OAuth2 username field."""
    tokens = await controller.login(form.username, form.password)
    return make_success_response(tokens)


@router.post("/refresh", response_model=SuccessEnvelope, status_code=status.HTTP_200_OK)
async def refresh_token(request: RefreshTokenRequest, controller: AuthCtrl):
    """Rotate a refresh token and issue a new token pair."""
    tokens = await controller.refresh(request.refresh_token)
    return make_success_response(tokens)


__all__ = ["router"]
