from __future__ import annotations

import base64
import binascii
from typing import Final, Protocol

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .compass_gateway import CompassGatewayError
from .principal import CompassPrincipal

_PUBLIC_PATHS: Final[set[str]] = {
    "/.well-known/agent-card.json",
    "/.well-known/agent.json",
    "/healthz",
}


class CompassAuthenticator(Protocol):
    async def authenticate(self, principal: CompassPrincipal) -> CompassPrincipal: ...


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


def add_basic_auth_middleware(app: FastAPI, authenticator: CompassAuthenticator) -> None:
    @app.middleware("http")
    async def basic_auth_middleware(request: Request, call_next):
        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)

        authorization = request.headers.get("Authorization", "")
        credentials = _decode_basic_credentials(authorization)
        if credentials is None:
            return _unauthorized_response()

        username, password = credentials
        if not username or not password:
            return _unauthorized_response()

        principal = CompassPrincipal(username=username, password=password)
        try:
            principal = await authenticator.authenticate(principal)
        except CompassGatewayError:
            return _unauthorized_response()

        request.state.compass_principal = principal
        return await call_next(request)
