"""Endpoint de autenticación."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.core.security import authenticate_user, create_access_token
from app.models.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Iniciar sesión",
    description="Valida las credenciales y devuelve un JWT de acceso.",
    responses={
        401: {"description": "Credenciales incorrectas."},
    },
)
async def login(request: LoginRequest) -> TokenResponse:
    user = authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(user["username"])
    return TokenResponse(
        access_token=token,
        username=user["username"],
        full_name=user["full_name"],
    )
