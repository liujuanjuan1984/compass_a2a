from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from .read_skills import ReadSkillInvocation, parse_read_skill_invocation
from .write_commands import WriteCommandInvocation, parse_write_command_invocation

InvocationKind = Literal["read_skill", "write_command"]


@dataclass(frozen=True)
class CapabilityInvocation:
    kind: InvocationKind
    name: str
    arguments: dict[str, Any]


def parse_capability_invocation(
    *,
    metadata: dict[str, Any] | None,
    user_input: str,
) -> CapabilityInvocation | None:
    read_skill = parse_read_skill_invocation(metadata=metadata, user_input=user_input)
    if isinstance(read_skill, ReadSkillInvocation):
        return CapabilityInvocation(
            kind="read_skill",
            name=read_skill.skill,
            arguments=read_skill.arguments,
        )

    write_command = parse_write_command_invocation(metadata=metadata)
    if isinstance(write_command, WriteCommandInvocation):
        return CapabilityInvocation(
            kind="write_command",
            name=write_command.command,
            arguments=write_command.arguments,
        )

    return None
