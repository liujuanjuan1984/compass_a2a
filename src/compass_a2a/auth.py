from __future__ import annotations

import base64
import binascii
import secrets
from typing import Final

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .config import Settings

_PUBLIC_PATHS: Final[set[str]] = {
    "/.well-known/agent-card.json",
    "/.well-known/agent.json",
    "/healthz",
}


def _unauthorized_response() -> JSONResponse:
    return JSONResponse(
        {"detail": "Unauthorized"},
        status_code=401,
        headers={"WWW-Authenticate": "Basic"},
    )


def _decode_basic_credentials(header_value: str) -> tuple[str, str] | None:
    if not header_value.startswith("Basic "):
        return None

    token = header_value[6:].strip()
    if not token:
        return None

    try:
        decoded = base64.b64decode(token).decode("utf-8")
    except (ValueError, UnicodeDecodeError, binascii.Error):
        return None

    if ":" not in decoded:
        return None

    username, password = decoded.split(":", 1)
    return username, password


def add_basic_auth_middleware(app: FastAPI, settings: Settings) -> None:
    @app.middleware("http")
    async def basic_auth_middleware(request: Request, call_next):
        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)

        authorization = request.headers.get("Authorization", "")
        credentials = _decode_basic_credentials(authorization)
        if credentials is None:
            return _unauthorized_response()

        username, password = credentials
        username_ok = secrets.compare_digest(username, settings.auth_username)
        password_ok = secrets.compare_digest(password, settings.auth_password)
        if not (username_ok and password_ok):
            return _unauthorized_response()

        request.state.user_identity = username
        return await call_next(request)
