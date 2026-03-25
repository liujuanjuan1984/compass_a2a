from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

SKILL_REVIEW_TIME_AND_ACTIVITY = "review_time_and_activity"
SKILL_SEARCH_PERSONAL_KNOWLEDGE = "search_personal_knowledge"
SKILL_REVIEW_PLANNING = "review_planning"
SKILL_REVIEW_FINANCE_STATE = "review_finance_state"
SKILL_REVIEW_VISION_FOCUS = "review_vision_focus"

SUPPORTED_SKILLS = {
    SKILL_REVIEW_TIME_AND_ACTIVITY,
    SKILL_SEARCH_PERSONAL_KNOWLEDGE,
    SKILL_REVIEW_PLANNING,
    SKILL_REVIEW_FINANCE_STATE,
    SKILL_REVIEW_VISION_FOCUS,
}


@dataclass(frozen=True)
class SkillInvocation:
    skill: str
    arguments: dict[str, Any]


def parse_skill_invocation(
    *,
    metadata: dict[str, Any] | None,
    user_input: str,
) -> SkillInvocation | None:
    compass_metadata = metadata.get("compass") if isinstance(metadata, dict) else None
    if isinstance(compass_metadata, dict):
        skill = compass_metadata.get("skill")
        arguments = compass_metadata.get("arguments")
        if isinstance(skill, str) and skill in SUPPORTED_SKILLS:
            return SkillInvocation(
                skill=skill,
                arguments=arguments if isinstance(arguments, dict) else {},
            )

    stripped = user_input.strip()
    if not stripped.startswith("/"):
        return None

    head, _, tail = stripped.partition(" ")
    skill = head[1:].strip()
    if skill not in SUPPORTED_SKILLS:
        return None

    if not tail.strip():
        return SkillInvocation(skill=skill, arguments={})

    try:
        parsed = json.loads(tail)
    except json.JSONDecodeError:
        return SkillInvocation(skill=skill, arguments={"raw_input": tail.strip()})

    return SkillInvocation(skill=skill, arguments=parsed if isinstance(parsed, dict) else {})


def render_skill_help() -> str:
    skills = ", ".join(sorted(SUPPORTED_SKILLS))
    return (
        "Compass adapter bootstrap skills are available via request metadata "
        "`metadata.compass.skill` + `metadata.compass.arguments`, or via "
        "slash-style text commands.\n\n"
        f"Available skills: {skills}"
    )
