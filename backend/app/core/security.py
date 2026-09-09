"""Autenticación: usuarios hardcodeados + JWT.

Para cambiar contraseñas: edita _RAW_USERS y reinicia el servidor.
Los hashes se generan con bcrypt en el arranque; no se almacenan en disco.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings

# ── Usuarios hardcodeados ─────────────────────────────────────────────────────
# Modifica username / password aquí y reinicia. No uses estas credenciales
# en producción sin cambiarlas.
_RAW_USERS = [
    {"username": "Soportehibot",     "password": "Hibot2026*",      "full_name": "Soporte Hibot",    "db": "default"},
    {"username": "HibotCS", "password": "CSHibot2026*", "full_name": "Equipo CS", "db": "default"},
    {"username": "AdminGC",     "password": "Grupocesa2026*",     "full_name": "Grupo CESA",       "db": "default"},
    {"username": "Eliasmx",    "password": "Hibot2026*",     "full_name": "Elias MX",       "db": "default"},
    {"username": "adminTP",   "password": "TPHibot2026*",    "full_name": "Admin TP",         "db": "tp"},
]

# Los hashes se calculan una sola vez al importar el módulo.
USERS_DB: dict[str, dict] = {
    u["username"]: {
        "username": u["username"],
        "full_name": u["full_name"],
        "db": u["db"],
        "hashed_password": bcrypt.hashpw(u["password"].encode(), bcrypt.gensalt()),
    }
    for u in _RAW_USERS
}


def authenticate_user(username: str, password: str) -> dict | None:
    """Devuelve el usuario si las credenciales son válidas, o None."""
    user = USERS_DB.get(username)
    if not user:
        return None
    if not bcrypt.checkpw(password.encode(), user["hashed_password"]):
        return None
    return user


def create_access_token(username: str) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode(
        {"sub": username, "exp": expire},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> str:
    """Devuelve el username del token o lanza JWTError si es inválido/expirado."""
    settings = get_settings()
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    username: str = payload.get("sub", "")
    if not username:
        raise JWTError("Token sin subject.")
    return username
