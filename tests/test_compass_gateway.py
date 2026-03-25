from __future__ import annotations

import json

import httpx
import pytest

from compass_a2a.compass_gateway import CompassGateway
from compass_a2a.config import Settings
from compass_a2a.principal import CompassPrincipal


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

    gateway = CompassGateway(Settings(compass_api_base_url="http://compass.test"))
    principal = CompassPrincipal(username="user@example.com", password="secret")

    await gateway.authenticate(principal)

    content = await gateway.invoke("review_planning", {"view_type": "day"}, principal)

    assert content == "planning ok"
    assert requests_seen == [
        ("POST", "/auth/login", None),
        ("POST", "/agentic/planning", "Bearer first-token"),
        ("POST", "/auth/login", None),
        ("POST", "/agentic/planning", "Bearer second-token"),
    ]


@pytest.mark.anyio
async def test_gateway_caches_tokens_per_compass_principal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests_seen: list[tuple[str, str, str | None]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        authorization = request.headers.get("Authorization")
        requests_seen.append((request.method, request.url.path, authorization))

        if request.url.path == "/auth/login":
            payload = request.read().decode("utf-8")
            if "alice@example.com" in payload:
                return httpx.Response(200, json={"access_token": "alice-token"})
            if "bob@example.com" in payload:
                return httpx.Response(200, json={"access_token": "bob-token"})
            return httpx.Response(401, json={"detail": "bad credentials"})

        if request.url.path == "/agentic/planning":
            return httpx.Response(200, json={"content": authorization or "missing"})

        return httpx.Response(500, json={"detail": "unexpected"})

    transport = httpx.MockTransport(handler)
    original_async_client = httpx.AsyncClient

    def build_client(*args, **kwargs):  # noqa: ANN001, ANN202
        kwargs["transport"] = transport
        return original_async_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", build_client)

    gateway = CompassGateway(Settings(compass_api_base_url="http://compass.test"))
    alice_first = CompassPrincipal(username="alice@example.com", password="secret")
    alice_second = CompassPrincipal(username="alice@example.com", password="secret")
    bob = CompassPrincipal(username="bob@example.com", password="secret")

    await gateway.authenticate(alice_first)
    await gateway.authenticate(alice_second)
    alice_content = await gateway.invoke(
        "review_planning",
        {"view_type": "day"},
        alice_second,
    )

    await gateway.authenticate(bob)
    bob_content = await gateway.invoke("review_planning", {"view_type": "week"}, bob)

    assert alice_content == "Bearer alice-token"
    assert bob_content == "Bearer bob-token"
    assert requests_seen == [
        ("POST", "/auth/login", None),
        ("POST", "/agentic/planning", "Bearer alice-token"),
        ("POST", "/auth/login", None),
        ("POST", "/agentic/planning", "Bearer bob-token"),
    ]


@pytest.mark.anyio
async def test_gateway_does_not_inject_default_locale(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planning_payloads: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/auth/login":
            return httpx.Response(200, json={"access_token": "planning-token"})

        if request.url.path == "/agentic/planning":
            planning_payloads.append(json.loads(request.content.decode()))
            return httpx.Response(200, json={"content": "planning ok"})

        return httpx.Response(500, json={"detail": "unexpected"})

    transport = httpx.MockTransport(handler)
    original_async_client = httpx.AsyncClient

    def build_client(*args, **kwargs):  # noqa: ANN001, ANN202
        kwargs["transport"] = transport
        return original_async_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", build_client)

    gateway = CompassGateway(Settings(compass_api_base_url="http://compass.test"))
    principal = CompassPrincipal(username="user@example.com", password="secret")

    await gateway.authenticate(principal)
    await gateway.invoke("review_planning", {"view_type": "day"}, principal)

    assert planning_payloads == [{"view_type": "day"}]
