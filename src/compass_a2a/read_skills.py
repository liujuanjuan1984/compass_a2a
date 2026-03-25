from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from a2a.types import AgentSkill

SKILL_REVIEW_TIME_AND_ACTIVITY = "review_time_and_activity"
SKILL_SEARCH_PERSONAL_KNOWLEDGE = "search_personal_knowledge"
SKILL_REVIEW_PLANNING = "review_planning"
SKILL_REVIEW_FINANCE_STATE = "review_finance_state"
SKILL_REVIEW_VISION_FOCUS = "review_vision_focus"

SUPPORTED_READ_SKILLS = {
    SKILL_REVIEW_TIME_AND_ACTIVITY,
    SKILL_SEARCH_PERSONAL_KNOWLEDGE,
    SKILL_REVIEW_PLANNING,
    SKILL_REVIEW_FINANCE_STATE,
    SKILL_REVIEW_VISION_FOCUS,
}


@dataclass(frozen=True)
class ReadSkillInvocation:
    skill: str
    arguments: dict[str, Any]


def parse_read_skill_invocation(
    *,
    metadata: dict[str, Any] | None,
    user_input: str,
) -> ReadSkillInvocation | None:
    compass_metadata = metadata.get("compass") if isinstance(metadata, dict) else None
    if isinstance(compass_metadata, dict):
        skill = compass_metadata.get("skill")
        arguments = compass_metadata.get("arguments")
        if isinstance(skill, str) and skill in SUPPORTED_READ_SKILLS:
            return ReadSkillInvocation(
                skill=skill,
                arguments=arguments if isinstance(arguments, dict) else {},
            )

    stripped = user_input.strip()
    if not stripped.startswith("/"):
        return None

    head, _, tail = stripped.partition(" ")
    skill = head[1:].strip()
    if skill not in SUPPORTED_READ_SKILLS:
        return None

    if not tail.strip():
        return ReadSkillInvocation(skill=skill, arguments={})

    try:
        parsed = json.loads(tail)
    except json.JSONDecodeError:
        return ReadSkillInvocation(skill=skill, arguments={"raw_input": tail.strip()})

    return ReadSkillInvocation(skill=skill, arguments=parsed if isinstance(parsed, dict) else {})


def render_read_skill_help() -> str:
    skills = ", ".join(sorted(SUPPORTED_READ_SKILLS))
    return (
        "Read skills are available via request metadata "
        "`metadata.compass.skill` + `metadata.compass.arguments`, or via "
        "slash-style text commands.\n\n"
        f"Available read skills: {skills}"
    )


def build_read_skill_catalog() -> list[AgentSkill]:
    return [
        AgentSkill(
            id=SKILL_REVIEW_TIME_AND_ACTIVITY,
            name="Review Time And Activity",
            description=(
                "Review time and activity context by routing through "
                "Compass timelog agentic exports."
            ),
            tags=["compass", "timelog", "review", "activity", "read"],
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
            tags=["compass", "notes", "knowledge", "search", "read"],
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
            tags=["compass", "planning", "review", "tasks", "read"],
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
            tags=["compass", "finance", "accounts", "cashflow", "trading", "read"],
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
            tags=["compass", "vision", "planning", "focus", "read"],
            examples=[
                "Review one vision with its subtasks.",
                "Load a vision summary with notes excluded.",
            ],
            security=[{"basicAuth": []}],
        ),
    ]
