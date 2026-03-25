# compass_a2a

`compass_a2a` is the dedicated A2A adapter service for Compass.

It is intentionally positioned as a separate process boundary:

- Compass stays the source of truth for LifeOS data and domain rules.
- `compass_a2a` exposes an A2A-facing runtime surface for hub and peer agents.
- The adapter can evolve independently from Compass internals.

## Bootstrap Scope

This repository is initialized with:

- `uv` for dependency and environment management
- `pre-commit` for basic code quality checks
- a minimal A2A server surface
- a public agent card endpoint
- HTTP Basic authentication for runtime access

The initial bootstrap account is:

- username: `compass`
- password: `compass`

Override them in the environment before production use.

## Quick Start

```bash
uv sync --extra dev
cp .env.example .env
uv run pre-commit install
uv run compass-a2a
```

By default the server listens on `http://127.0.0.1:8000`.

Public endpoints:

- `GET /.well-known/agent-card.json`
- `GET /.well-known/agent.json`
- `GET /healthz`

Protected endpoints:

- `POST /`
- `POST /v1/message:send`
- `POST /v1/message:stream`
- `GET /v1/card`

## Authentication

Runtime access uses HTTP Basic authentication.

Environment variables:

- `COMPASS_A2A_AUTH_USERNAME`
- `COMPASS_A2A_AUTH_PASSWORD`

The authenticated username is propagated into the request context so later
Compass-facing logic can apply user-aware routing and policy.

## Development

Run checks:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

## Roadmap

This bootstrap intentionally keeps the runtime thin. The next steps are expected
to include:

- Compass API integration
- approval-aware write operations
- richer task execution and streaming behavior
- durable task/session storage
