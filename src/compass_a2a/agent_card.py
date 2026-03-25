from __future__ import annotations

from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentProvider,
    HTTPAuthSecurityScheme,
    SecurityScheme,
)

from .config import Settings
from .read_skills import build_read_skill_catalog


def build_agent_card(settings: Settings) -> AgentCard:
    base_url = settings.public_url.rstrip("/")
    return AgentCard(
        name="compass-a2a",
        description=(
            "A thin A2A adapter service for Compass. "
            "It exposes Compass-oriented capabilities through an authenticated "
            "A2A surface backed by Compass account credentials."
        ),
        url=base_url,
        version=settings.adapter_version,
        protocol_version=settings.protocol_version,
        preferred_transport="JSONRPC",
        additional_interfaces=[
            AgentInterface(transport="JSONRPC", url=base_url),
            AgentInterface(transport="HTTP+JSON", url=base_url),
        ],
        provider=AgentProvider(
            organization="liujuanjuan1984",
            url="https://github.com/liujuanjuan1984/compass-a2a",
        ),
        capabilities=AgentCapabilities(
            streaming=True,
            push_notifications=False,
            state_transition_history=False,
        ),
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        skills=build_read_skill_catalog(),
        security_schemes={
            "basicAuth": SecurityScheme(
                root=HTTPAuthSecurityScheme(
                    scheme="Basic",
                    description=("HTTP Basic authentication using Compass account credentials."),
                )
            )
        },
        security=[{"basicAuth": []}],
        supports_authenticated_extended_card=True,
    )
