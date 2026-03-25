from __future__ import annotations

from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentProvider,
    AgentSkill,
    HTTPAuthSecurityScheme,
    SecurityScheme,
)

from .config import Settings


def build_agent_card(settings: Settings) -> AgentCard:
    base_url = settings.public_url.rstrip("/")
    return AgentCard(
        name="Compass A2A Adapter",
        description=(
            "A thin A2A adapter service for Compass. "
            "It exposes Compass-oriented capabilities through an authenticated A2A surface."
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
            url="https://github.com/liujuanjuan1984/compass_a2a",
        ),
        capabilities=AgentCapabilities(
            streaming=True,
            push_notifications=False,
            state_transition_history=False,
        ),
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        skills=[
            AgentSkill(
                id="compass_adapter_chat",
                name="Compass Adapter Chat",
                description=(
                    "Bootstrap skill for Compass adapter interactions. "
                    "It accepts text requests and returns Compass-oriented adapter responses."
                ),
                tags=["compass", "a2a", "adapter", "lifeos"],
                examples=[
                    "Summarize today's Compass context.",
                    "Prepare a Compass adapter task for timelog review.",
                ],
                security=[{"basicAuth": []}],
            )
        ],
        security_schemes={
            "basicAuth": SecurityScheme(
                root=HTTPAuthSecurityScheme(
                    scheme="Basic",
                    description="HTTP Basic authentication for adapter access.",
                )
            )
        },
        security=[{"basicAuth": []}],
        supports_authenticated_extended_card=True,
    )
