from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .read_skills import CapabilityContractError

SUPPORTED_WRITE_COMMANDS: frozenset[str] = frozenset()


@dataclass(frozen=True)
class WriteCommandInvocation:
    command: str
    arguments: dict[str, Any]


def parse_write_command_invocation(
    *,
    metadata: dict[str, Any] | None,
) -> WriteCommandInvocation | None:
    compass_metadata = metadata.get("compass") if isinstance(metadata, dict) else None
    if not isinstance(compass_metadata, dict):
        return None

    command = compass_metadata.get("command")
    arguments = compass_metadata.get("arguments")
    if command is None:
        return None
    if not isinstance(command, str) or not command.strip():
        raise CapabilityContractError("metadata.compass.command must be a non-empty string")

    normalized_command = command.strip()
    if normalized_command not in SUPPORTED_WRITE_COMMANDS:
        raise CapabilityContractError(f"Unsupported write command: {normalized_command}")

    if arguments is None:
        normalized_arguments: dict[str, Any] = {}
    elif isinstance(arguments, dict):
        normalized_arguments = dict(arguments)
    else:
        raise CapabilityContractError("capability arguments must be an object")

    return WriteCommandInvocation(
        command=normalized_command,
        arguments=normalized_arguments,
    )


def render_write_command_help() -> str:
    if not SUPPORTED_WRITE_COMMANDS:
        return (
            "Write commands are routed through a dedicated command execution path.\n\n"
            "Available write commands: none enabled yet"
        )

    commands = ", ".join(sorted(SUPPORTED_WRITE_COMMANDS))
    return (
        "Write commands are available via request metadata "
        "`metadata.compass.command` + `metadata.compass.arguments`.\n\n"
        f"Available write commands: {commands}"
    )
