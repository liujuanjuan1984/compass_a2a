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

SUPPORTED_PLANNING_VIEW_TYPES = {"day", "week", "month", "year"}


class CapabilityContractError(ValueError):
    pass


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
        if skill is not None:
            if not isinstance(skill, str) or not skill.strip():
                raise CapabilityContractError("metadata.compass.skill must be a non-empty string")
            normalized_skill = skill.strip()
            if normalized_skill not in SUPPORTED_READ_SKILLS:
                raise CapabilityContractError(f"Unsupported read skill: {normalized_skill}")
            normalized_arguments = _normalize_arguments(arguments)
            return ReadSkillInvocation(
                skill=normalized_skill,
                arguments=_validate_read_skill_arguments(normalized_skill, normalized_arguments),
            )

    stripped = user_input.strip()
    if not stripped.startswith("/"):
        return None

    head, _, tail = stripped.partition(" ")
    skill = head[1:].strip()
    if skill not in SUPPORTED_READ_SKILLS:
        raise CapabilityContractError(f"Unsupported read skill: {skill}")

    if not tail.strip():
        return ReadSkillInvocation(skill=skill, arguments={})

    try:
        parsed = json.loads(tail)
    except json.JSONDecodeError as exc:
        raise CapabilityContractError(
            "slash-style read skill arguments must be a JSON object"
        ) from exc

    if not isinstance(parsed, dict):
        raise CapabilityContractError("slash-style read skill arguments must be a JSON object")

    return ReadSkillInvocation(skill=skill, arguments=_validate_read_skill_arguments(skill, parsed))


def render_read_skill_help() -> str:
    skills = ", ".join(sorted(SUPPORTED_READ_SKILLS))
    return (
        "Read skills are available via request metadata "
        "`metadata.compass.skill` + `metadata.compass.arguments`, or via "
        "slash-style text commands.\n\n"
        f"Available read skills: {skills}"
    )


def _normalize_arguments(arguments: Any) -> dict[str, Any]:
    if arguments is None:
        return {}
    if not isinstance(arguments, dict):
        raise CapabilityContractError("capability arguments must be an object")
    return dict(arguments)


def _validate_read_skill_arguments(skill: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if skill == SKILL_REVIEW_PLANNING:
        view_type = arguments.get("view_type")
        if view_type is not None:
            if not isinstance(view_type, str) or view_type not in SUPPORTED_PLANNING_VIEW_TYPES:
                allowed = "|".join(sorted(SUPPORTED_PLANNING_VIEW_TYPES))
                raise CapabilityContractError(
                    f"review_planning requires view_type={allowed} when provided"
                )

    if skill == SKILL_REVIEW_FINANCE_STATE:
        target = arguments.get("target")
        if target is not None:
            if not isinstance(target, str) or target not in {"accounts", "cashflow", "trading"}:
                raise CapabilityContractError(
                    "review_finance_state requires target=accounts|cashflow|trading"
                )

    if skill == SKILL_REVIEW_VISION_FOCUS:
        vision_id = arguments.get("vision_id")
        if not isinstance(vision_id, str) or not vision_id.strip():
            raise CapabilityContractError("review_vision_focus requires vision_id")
        for field_name in ("include_subtasks", "include_notes", "include_time_records"):
            value = arguments.get(field_name)
            if value is not None and not isinstance(value, bool):
                raise CapabilityContractError(f"review_vision_focus requires boolean {field_name}")

    return arguments


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
