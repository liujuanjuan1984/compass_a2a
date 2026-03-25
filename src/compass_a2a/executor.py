from __future__ import annotations

from typing import Protocol

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import (
    Artifact,
    Message,
    Role,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
    TextPart,
)

from .capabilities import parse_capability_invocation
from .compass_gateway import CompassGatewayError
from .config import Settings
from .principal import CompassPrincipal
from .read_skills import render_read_skill_help
from .write_commands import render_write_command_help


class CapabilityGateway(Protocol):
    async def invoke_read_skill(
        self, skill: str, arguments: dict[str, object], principal: CompassPrincipal
    ) -> str: ...

    async def execute_write_command(
        self, command: str, arguments: dict[str, object], principal: CompassPrincipal
    ) -> str: ...


class CompassAdapterExecutor(AgentExecutor):
    def __init__(self, settings: Settings, gateway: CapabilityGateway) -> None:
        self._settings = settings
        self._gateway = gateway

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task_id = context.task_id or "compass-task"
        context_id = context.context_id or "compass-context"
        user_input = context.get_user_input().strip() or "No input provided."
        principal = self._extract_principal(context)
        identity = principal.identity if principal else "anonymous"

        working_message = self._build_agent_message(
            text="Compass adapter is processing the request.",
            context_id=context_id,
            message_id=f"{task_id}:working",
        )
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=task_id,
                context_id=context_id,
                final=False,
                status=TaskStatus(
                    state=TaskState.working,
                    message=working_message,
                ),
            )
        )

        invocation = parse_capability_invocation(
            metadata=context.metadata,
            user_input=user_input,
        )
        if invocation is None:
            response_text = (
                f"Authenticated identity: {identity}\n"
                f"Compass API base URL: {self._settings.compass_api_base_url}\n\n"
                f"{render_read_skill_help()}\n\n{render_write_command_help()}"
            )
            final_state = TaskState.completed
        else:
            try:
                if principal is None:
                    raise CompassGatewayError("Missing authenticated Compass principal")
                if invocation.kind == "read_skill":
                    content = await self._gateway.invoke_read_skill(
                        invocation.name,
                        invocation.arguments,
                        principal,
                    )
                    action_label = f"Read skill: {invocation.name}"
                else:
                    content = await self._gateway.execute_write_command(
                        invocation.name,
                        invocation.arguments,
                        principal,
                    )
                    action_label = f"Write command: {invocation.name}"
                response_text = f"{action_label}\nAuthenticated identity: {identity}\n\n{content}"
                final_state = TaskState.completed
            except CompassGatewayError as exc:
                response_text = (
                    f"{invocation.kind.replace('_', ' ').title()}: {invocation.name}\n"
                    f"Authenticated identity: {identity}\n\n"
                    f"Compass gateway error: {exc}"
                )
                final_state = TaskState.failed

        await event_queue.enqueue_event(
            TaskArtifactUpdateEvent(
                task_id=task_id,
                context_id=context_id,
                artifact=Artifact(
                    artifact_id=f"{task_id}:response",
                    name="compass-adapter-response",
                    description="Bootstrap Compass adapter response artifact.",
                    parts=[TextPart(text=response_text)],
                ),
                last_chunk=True,
            )
        )

        completed_message = self._build_agent_message(
            text=response_text,
            context_id=context_id,
            message_id=f"{task_id}:completed",
        )
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=task_id,
                context_id=context_id,
                final=True,
                status=TaskStatus(
                    state=final_state,
                    message=completed_message,
                ),
            )
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        task_id = context.task_id or "compass-task"
        context_id = context.context_id or "compass-context"
        canceled_message = self._build_agent_message(
            text="Compass adapter request canceled.",
            context_id=context_id,
            message_id=f"{task_id}:canceled",
        )
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=task_id,
                context_id=context_id,
                final=True,
                status=TaskStatus(
                    state=TaskState.canceled,
                    message=canceled_message,
                ),
            )
        )

    @staticmethod
    def _extract_principal(context: RequestContext) -> CompassPrincipal | None:
        call_context = context.call_context
        if not call_context:
            return None
        principal = call_context.state.get("compass_principal")
        return principal if isinstance(principal, CompassPrincipal) else None

    @staticmethod
    def _build_agent_message(*, text: str, context_id: str, message_id: str) -> Message:
        return Message(
            message_id=message_id,
            context_id=context_id,
            role=Role.agent,
            parts=[TextPart(text=text)],
        )
