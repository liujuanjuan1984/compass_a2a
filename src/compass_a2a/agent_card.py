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
from .skills import (
    SKILL_REVIEW_FINANCE_STATE,
    SKILL_REVIEW_PLANNING,
    SKILL_REVIEW_TIME_AND_ACTIVITY,
    SKILL_REVIEW_VISION_FOCUS,
    SKILL_SEARCH_PERSONAL_KNOWLEDGE,
)


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
        skills=[
            AgentSkill(
                id=SKILL_REVIEW_TIME_AND_ACTIVITY,
                name="Review Time And Activity",
                description=(
                    "Review time and activity context by routing through "
                    "Compass timelog agentic exports."
                ),
                tags=["compass", "timelog", "review", "activity"],
                examples=[
                    "Review today's time and activity context.",
                    "Summarize recent timelog activity for the last 3 days.",
                ],
                security=[{"basicAuth": []}],
            ),
            AgentSkill(
                id=SKILL_SEARCH_PERSONAL_KNOWLEDGE,
                name="Search Personal Knowledge",
                description="Search personal knowledge through Compass notes agentic exports.",
                tags=["compass", "notes", "knowledge", "search"],
                examples=[
                    "Search my notes for recent mentions of A2A.",
                    "Summarize the notes related to planning.",
                ],
                security=[{"basicAuth": []}],
            ),
            AgentSkill(
                id=SKILL_REVIEW_PLANNING,
                name="Review Planning",
                description=(
                    "Review day, week, month, or year planning through Compass planning exports."
                ),
                tags=["compass", "planning", "review", "tasks"],
                examples=[
                    "Show the day plan for today.",
                    "Review the week plan with notes included.",
                ],
                security=[{"basicAuth": []}],
            ),
            AgentSkill(
                id=SKILL_REVIEW_FINANCE_STATE,
                name="Review Finance State",
                description=(
                    "Review finance state via Compass finance agentic exports "
                    "for accounts, cashflow, or trading."
                ),
                tags=["compass", "finance", "accounts", "cashflow", "trading"],
                examples=[
                    "Show the finance account tree summary.",
                    "Review recent cashflow.",
                ],
                security=[{"basicAuth": []}],
            ),
            AgentSkill(
                id=SKILL_REVIEW_VISION_FOCUS,
                name="Review Vision Focus",
                description="Review a vision with related subtasks, notes, and time records.",
                tags=["compass", "vision", "planning", "focus"],
                examples=[
                    "Review one vision with its subtasks.",
                    "Load a vision summary with notes excluded.",
                ],
                security=[{"basicAuth": []}],
            ),
        ],
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
