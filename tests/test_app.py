from __future__ import annotations

import base64
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from a2a.types import Message, MessageSendParams, Role, SendMessageRequest, TextPart

from compass_a2a.app import build_app
from compass_a2a.config import Settings
from compass_a2a.skills import SKILL_REVIEW_PLANNING


class FakeGateway:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def invoke(self, skill: str, arguments: dict[str, object]) -> str:
        self.calls.append((skill, arguments))
        return f"gateway:{skill}"


def _auth_header(username: str, password: str) -> dict[str, str]:
    token = base64.b64encode(f"{username}:{password}".encode()).decode("ascii")
    return {"Authorization": f"Basic {token}"}


def _build_client() -> TestClient:
    settings = Settings(
        auth_username="compass",
        auth_password="compass",
        public_url="http://testserver",
        compass_api_base_url="http://compass.test/api/v1",
    )
    return TestClient(build_app(settings, gateway=FakeGateway()))


def test_healthz_is_public() -> None:
    client = _build_client()

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_agent_card_is_public_and_declares_basic_auth() -> None:
    client = _build_client()

    response = client.get("/.well-known/agent-card.json")

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "Compass A2A Adapter"
    assert payload["securitySchemes"]["basicAuth"]["scheme"] == "Basic"
    skill_ids = {skill["id"] for skill in payload["skills"]}
    assert SKILL_REVIEW_PLANNING in skill_ids


def test_jsonrpc_message_send_requires_auth() -> None:
    client = _build_client()
    request = SendMessageRequest(
        id="req-1",
        method="message/send",
        params=MessageSendParams(
            message=Message(
                message_id="msg-1",
                role=Role.user,
                parts=[TextPart(text="hello compass")],
            )
        ),
    )

    response = client.post("/", json=request.model_dump(mode="json", by_alias=True))

    assert response.status_code == 401


def test_jsonrpc_message_send_returns_completed_task_when_authenticated() -> None:
    client = _build_client()
    request = SendMessageRequest(
        id="req-1",
        method="message/send",
        params=MessageSendParams(
            message=Message(
                message_id="msg-1",
                role=Role.user,
                parts=[TextPart(text="hello compass")],
            )
        ),
    )

    response = client.post(
        "/",
        json=request.model_dump(mode="json", by_alias=True),
        headers=_auth_header("compass", "compass"),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["result"]["status"]["state"] == "completed"
    response_text = payload["result"]["artifacts"][0]["parts"][0]["text"]
    assert "Available skills:" in response_text


def test_jsonrpc_message_send_dispatches_skill_through_gateway_metadata() -> None:
    gateway = FakeGateway()
    settings = Settings(
        auth_username="compass",
        auth_password="compass",
        public_url="http://testserver",
        compass_api_base_url="http://compass.test/api/v1",
    )
    client = TestClient(build_app(settings, gateway=gateway))
    request = SendMessageRequest(
        id="req-2",
        method="message/send",
        params=MessageSendParams(
            message=Message(
                message_id="msg-2",
                role=Role.user,
                parts=[TextPart(text="review planning")],
            ),
            metadata={
                "compass": {
                    "skill": SKILL_REVIEW_PLANNING,
                    "arguments": {"view_type": "day"},
                }
            },
        ),
    )

    response = client.post(
        "/",
        json=request.model_dump(mode="json", by_alias=True),
        headers=_auth_header("compass", "compass"),
    )

    assert response.status_code == 200
    assert gateway.calls == [(SKILL_REVIEW_PLANNING, {"view_type": "day"})]
    payload = response.json()
    response_text = payload["result"]["artifacts"][0]["parts"][0]["text"]
    assert "gateway:review_planning" in response_text
