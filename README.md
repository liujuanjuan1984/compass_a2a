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
- HTTP Basic authentication bridged to Compass account credentials

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

The adapter does not maintain its own account system. Instead, the Basic Auth
username and password are treated as Compass login credentials. The current
authenticated Compass identity is propagated into the request context so later
Compass-facing logic can apply user-aware routing, token reuse, and policy.

The Basic Auth username should match the Compass login identifier currently
expected by Compass, which is typically the account email.

## Compass Bootstrap Skills

The current branch exposes a small bootstrap skill catalog while internally
using Compass `/agentic/*` facade endpoints as the initial data source.

- `review_time_and_activity`
- `search_personal_knowledge`
- `review_planning`
- `review_finance_state`
- `review_vision_focus`

Recommended invocation style is metadata-driven:

```json
{
  "compass": {
    "skill": "review_planning",
    "arguments": {
      "view_type": "day",
      "selected_date": "2026-03-25T00:00:00Z",
      "include_notes": true
    }
  }
}
```

For quick manual testing, slash-style text commands also work:

```text
/review_time_and_activity {"start_date":"2026-03-25T00:00:00Z","end_date":"2026-03-25T23:59:59Z"}
```

These Compass endpoints are treated as an internal bootstrap gateway, not as
the long-term external A2A contract. Authentication is also bridged through
Compass itself, so `compass_a2a` remains a thin protocol and policy layer.

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
