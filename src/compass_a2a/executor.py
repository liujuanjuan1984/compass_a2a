from __future__ import annotations

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

from .config import Settings


class CompassAdapterExecutor(AgentExecutor):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task_id = context.task_id or "compass-task"
        context_id = context.context_id or "compass-context"
        user_input = context.get_user_input().strip() or "No input provided."
        identity = self._extract_identity(context)

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

        response_text = (
            f"Compass adapter bootstrap received: {user_input}\n\n"
            f"Authenticated identity: {identity}\n"
            f"Compass base URL: {self._settings.compass_base_url}\n"
            "Next step: replace this bootstrap executor with real Compass domain orchestration."
        )

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
                    state=TaskState.completed,
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
    def _extract_identity(context: RequestContext) -> str:
        call_context = context.call_context
        if not call_context:
            return "anonymous"
        identity = call_context.state.get("identity")
        return identity if isinstance(identity, str) and identity else "anonymous"

    @staticmethod
    def _build_agent_message(*, text: str, context_id: str, message_id: str) -> Message:
        return Message(
            message_id=message_id,
            context_id=context_id,
            role=Role.agent,
            parts=[TextPart(text=text)],
        )
