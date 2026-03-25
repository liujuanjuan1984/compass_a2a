from __future__ import annotations

import httpx
import pytest

from compass_a2a.compass_gateway import CompassGateway
from compass_a2a.config import Settings


@pytest.mark.anyio
async def test_gateway_reauthenticates_after_unauthorized(monkeypatch: pytest.MonkeyPatch) -> None:
    requests_seen: list[tuple[str, str, str | None]] = []
    login_tokens = ["first-token", "second-token"]

    def handler(request: httpx.Request) -> httpx.Response:
        authorization = request.headers.get("Authorization")
        requests_seen.append((request.method, request.url.path, authorization))

        if request.url.path == "/auth/login":
            token = login_tokens.pop(0)
            return httpx.Response(200, json={"access_token": token})

        if request.url.path == "/agentic/planning":
            if authorization == "Bearer first-token":
                return httpx.Response(401, json={"detail": "expired"})
            if authorization == "Bearer second-token":
                return httpx.Response(200, json={"content": "planning ok"})

        return httpx.Response(500, json={"detail": "unexpected"})

    transport = httpx.MockTransport(handler)
    original_async_client = httpx.AsyncClient

    def build_client(*args, **kwargs):  # noqa: ANN001, ANN202
        kwargs["transport"] = transport
        return original_async_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", build_client)

    gateway = CompassGateway(
        Settings(
            compass_api_base_url="http://compass.test",
            compass_email="user@example.com",
            compass_password="secret",
        )
    )

    content = await gateway.invoke("review_planning", {"view_type": "day"})

    assert content == "planning ok"
    assert requests_seen == [
        ("POST", "/auth/login", None),
        ("POST", "/agentic/planning", "Bearer first-token"),
        ("POST", "/auth/login", None),
        ("POST", "/agentic/planning", "Bearer second-token"),
    ]
