from __future__ import annotations

from a2a.server.apps.jsonrpc.fastapi_app import A2AFastAPI, A2AFastAPIApplication
from a2a.server.apps.jsonrpc.jsonrpc_app import DefaultCallContextBuilder
from a2a.server.apps.rest.rest_adapter import RESTAdapter
from a2a.server.request_handlers.default_request_handler import DefaultRequestHandler
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from fastapi import FastAPI, Request

from .agent_card import build_agent_card
from .auth import add_basic_auth_middleware
from .compass_gateway import CompassGateway
from .config import Settings
from .executor import CompassAdapterExecutor
from .principal import CompassPrincipal


class IdentityAwareCallContextBuilder(DefaultCallContextBuilder):
    def build(self, request: Request):
        context = super().build(request)
        identity = getattr(request.state, "user_identity", None)
        if identity:
            context.state["identity"] = identity
        principal = getattr(request.state, "compass_principal", None)
        if isinstance(principal, CompassPrincipal):
            context.state["compass_principal"] = principal
        return context


def build_app(
    settings: Settings | None = None,
    gateway: CompassGateway | None = None,
) -> FastAPI:
    settings = settings or Settings()
    agent_card = build_agent_card(settings)
    gateway = gateway or CompassGateway(settings)
    handler = DefaultRequestHandler(
        agent_executor=CompassAdapterExecutor(settings, gateway),
        task_store=InMemoryTaskStore(),
    )
    context_builder = IdentityAwareCallContextBuilder()

    app = A2AFastAPI(title=settings.app_name, version=settings.adapter_version)
    app.get("/healthz")(lambda: {"status": "ok"})

    jsonrpc_app = A2AFastAPIApplication(
        agent_card=agent_card,
        http_handler=handler,
        context_builder=context_builder,
    )
    jsonrpc_app.add_routes_to_app(
        app,
        agent_card_url="/.well-known/agent-card.json",
        rpc_url="/",
        extended_agent_card_url="/v1/card",
    )

    rest_adapter = RESTAdapter(
        agent_card=agent_card,
        http_handler=handler,
        context_builder=context_builder,
    )
    for (path, method), callback in rest_adapter.routes().items():
        app.add_api_route(path, callback, methods=[method])

    add_basic_auth_middleware(app, gateway)
    return app


app = build_app()
