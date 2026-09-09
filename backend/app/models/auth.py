"""Modelos de autenticación."""
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(description="Nombre de usuario.")
    password: str = Field(description="Contraseña en texto plano.")


class TokenResponse(BaseModel):
    access_token: str = Field(description="JWT de acceso.")
    token_type: str = Field(default="bearer")
    username: str = Field(description="Nombre de usuario autenticado.")
    full_name: str = Field(description="Nombre completo del usuario.")
