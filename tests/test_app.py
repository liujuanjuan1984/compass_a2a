from __future__ import annotations

import base64
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from a2a.types import Message, MessageSendParams, Role, SendMessageRequest, TextPart

from compass_a2a.app import build_app
from compass_a2a.compass_gateway import CompassGatewayError
from compass_a2a.config import Settings
from compass_a2a.principal import CompassPrincipal
from compass_a2a.read_skills import SKILL_REVIEW_PLANNING


class FakeGateway:
    def __init__(self) -> None:
        self.auth_calls: list[tuple[str, str]] = []
        self.calls: list[tuple[str, dict[str, object], str]] = []

    async def authenticate(self, principal: CompassPrincipal) -> CompassPrincipal:
        self.auth_calls.append((principal.username, principal.password))
        if principal.password != "secret":
            raise CompassGatewayError("invalid credentials")
        principal.access_token = f"token:{principal.username}"
        return principal

    async def invoke_read_skill(
        self, skill: str, arguments: dict[str, object], principal: CompassPrincipal
    ) -> str:
        self.calls.append((skill, arguments, principal.identity))
        return f"gateway:{skill}"

    async def execute_write_command(
        self, command: str, arguments: dict[str, object], principal: CompassPrincipal
    ) -> str:
        self.calls.append((command, arguments, principal.identity))
        raise CompassGatewayError(f"write disabled: {command}")


def _auth_header(username: str, password: str) -> dict[str, str]:
    token = base64.b64encode(f"{username}:{password}".encode()).decode("ascii")
    return {"Authorization": f"Basic {token}"}


def _build_client(gateway: FakeGateway | None = None) -> TestClient:
    settings = Settings(
        public_url="http://testserver",
        compass_api_base_url="http://compass.test/api/v1",
    )
    return TestClient(build_app(settings, gateway=gateway or FakeGateway()))


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
    assert payload["name"] == "compass-a2a"
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
    gateway = FakeGateway()
    client = _build_client(gateway)
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
        headers=_auth_header("user@example.com", "secret"),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["result"]["status"]["state"] == "completed"
    response_text = payload["result"]["artifacts"][0]["parts"][0]["text"]
    assert "Available read skills:" in response_text
    assert "Available write commands: none enabled yet" in response_text
    assert "Authenticated identity: user@example.com" in response_text
    assert gateway.auth_calls == [("user@example.com", "secret")]


def test_jsonrpc_message_send_returns_unauthorized_for_invalid_compass_credentials() -> None:
    client = _build_client()
    request = SendMessageRequest(
        id="req-invalid",
        method="message/send",
        params=MessageSendParams(
            message=Message(
                message_id="msg-invalid",
                role=Role.user,
                parts=[TextPart(text="hello compass")],
            )
        ),
    )

    response = client.post(
        "/",
        json=request.model_dump(mode="json", by_alias=True),
        headers=_auth_header("user@example.com", "wrong-password"),
    )

    assert response.status_code == 401


def test_jsonrpc_message_send_dispatches_skill_through_gateway_metadata() -> None:
    gateway = FakeGateway()
    settings = Settings(
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
        headers=_auth_header("user@example.com", "secret"),
    )

    assert response.status_code == 200
    assert gateway.calls == [(SKILL_REVIEW_PLANNING, {"view_type": "day"}, "user@example.com")]
    payload = response.json()
    response_text = payload["result"]["artifacts"][0]["parts"][0]["text"]
    assert "gateway:review_planning" in response_text
    assert "Read skill: review_planning" in response_text


def test_jsonrpc_message_send_routes_write_command_through_dedicated_path() -> None:
    gateway = FakeGateway()
    client = _build_client(gateway)
    request = SendMessageRequest(
        id="req-3",
        method="message/send",
        params=MessageSendParams(
            message=Message(
                message_id="msg-3",
                role=Role.user,
                parts=[TextPart(text="create note")],
            ),
            metadata={
                "compass": {
                    "command": "create_note",
                    "arguments": {"title": "Test"},
                }
            },
        ),
    )

    response = client.post(
        "/",
        json=request.model_dump(mode="json", by_alias=True),
        headers=_auth_header("user@example.com", "secret"),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["result"]["status"]["state"] == "failed"
    response_text = payload["result"]["artifacts"][0]["parts"][0]["text"]
    assert "Capability contract error: Unsupported write command: create_note" in response_text
    assert gateway.calls == []


def test_jsonrpc_message_send_rejects_conflicting_skill_and_command_metadata() -> None:
    gateway = FakeGateway()
    client = _build_client(gateway)
    request = SendMessageRequest(
        id="req-4",
        method="message/send",
        params=MessageSendParams(
            message=Message(
                message_id="msg-4",
                role=Role.user,
                parts=[TextPart(text="review planning")],
            ),
            metadata={
                "compass": {
                    "skill": SKILL_REVIEW_PLANNING,
                    "command": "create_note",
                    "arguments": {"view_type": "day"},
                }
            },
        ),
    )

    response = client.post(
        "/",
        json=request.model_dump(mode="json", by_alias=True),
        headers=_auth_header("user@example.com", "secret"),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["result"]["status"]["state"] == "failed"
    response_text = payload["result"]["artifacts"][0]["parts"][0]["text"]
    assert "Capability contract error:" in response_text
    assert "must not provide both skill and command" in response_text
    assert gateway.calls == []


def test_jsonrpc_message_send_rejects_invalid_metadata_arguments_shape() -> None:
    gateway = FakeGateway()
    client = _build_client(gateway)
    request = SendMessageRequest(
        id="req-5",
        method="message/send",
        params=MessageSendParams(
            message=Message(
                message_id="msg-5",
                role=Role.user,
                parts=[TextPart(text="review planning")],
            ),
            metadata={
                "compass": {
                    "skill": SKILL_REVIEW_PLANNING,
                    "arguments": ["day"],
                }
            },
        ),
    )

    response = client.post(
        "/",
        json=request.model_dump(mode="json", by_alias=True),
        headers=_auth_header("user@example.com", "secret"),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["result"]["status"]["state"] == "failed"
    response_text = payload["result"]["artifacts"][0]["parts"][0]["text"]
    assert "Capability contract error: capability arguments must be an object" in response_text
    assert gateway.calls == []


def test_jsonrpc_message_send_rejects_invalid_slash_skill_payload() -> None:
    gateway = FakeGateway()
    client = _build_client(gateway)
    request = SendMessageRequest(
        id="req-6",
        method="message/send",
        params=MessageSendParams(
            message=Message(
                message_id="msg-6",
                role=Role.user,
                parts=[TextPart(text="/review_planning not-json")],
            )
        ),
    )

    response = client.post(
        "/",
        json=request.model_dump(mode="json", by_alias=True),
        headers=_auth_header("user@example.com", "secret"),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["result"]["status"]["state"] == "failed"
    response_text = payload["result"]["artifacts"][0]["parts"][0]["text"]
    assert "Capability contract error:" in response_text
    assert "slash-style read skill arguments must be a JSON object" in response_text
    assert gateway.calls == []
