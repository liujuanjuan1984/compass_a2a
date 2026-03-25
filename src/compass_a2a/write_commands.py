from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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
    if not isinstance(command, str) or not command.strip():
        return None

    return WriteCommandInvocation(
        command=command.strip(),
        arguments=arguments if isinstance(arguments, dict) else {},
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
