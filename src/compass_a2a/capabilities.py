from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from .read_skills import (
    CapabilityContractError,
    ReadSkillInvocation,
    parse_read_skill_invocation,
)
from .write_commands import WriteCommandInvocation, parse_write_command_invocation

InvocationKind = Literal["read_skill", "write_command"]


@dataclass(frozen=True)
class CapabilityInvocation:
    kind: InvocationKind
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class CapabilityParseResult:
    invocation: CapabilityInvocation | None = None
    error: str | None = None


def parse_capability_invocation(
    *,
    metadata: dict[str, Any] | None,
    user_input: str,
) -> CapabilityParseResult:
    try:
        if metadata is not None and not isinstance(metadata, dict):
            raise CapabilityContractError("request metadata must be an object when provided")

        compass_metadata = metadata.get("compass") if isinstance(metadata, dict) else None
        if compass_metadata is not None and not isinstance(compass_metadata, dict):
            raise CapabilityContractError("metadata.compass must be an object")

        if isinstance(compass_metadata, dict):
            has_skill = "skill" in compass_metadata
            has_command = "command" in compass_metadata
            if has_skill and has_command:
                raise CapabilityContractError(
                    "metadata.compass must not provide both skill and command"
                )
            if not has_skill and not has_command and compass_metadata:
                raise CapabilityContractError(
                    "metadata.compass must provide either skill or command"
                )

        read_skill = parse_read_skill_invocation(metadata=metadata, user_input=user_input)
        if isinstance(read_skill, ReadSkillInvocation):
            return CapabilityParseResult(
                invocation=CapabilityInvocation(
                    kind="read_skill",
                    name=read_skill.skill,
                    arguments=read_skill.arguments,
                )
            )

        write_command = parse_write_command_invocation(metadata=metadata)
        if isinstance(write_command, WriteCommandInvocation):
            return CapabilityParseResult(
                invocation=CapabilityInvocation(
                    kind="write_command",
                    name=write_command.command,
                    arguments=write_command.arguments,
                )
            )
    except CapabilityContractError as exc:
        return CapabilityParseResult(error=str(exc))

    return CapabilityParseResult()
