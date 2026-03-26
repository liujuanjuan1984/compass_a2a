# compass-a2a

> Expose Compass through A2A.

`compass-a2a` is a thin A2A adapter in front of Compass.

It exists to keep a clean service boundary:

- Compass remains the source of truth for identity, data, and domain rules.
- `compass-a2a` exposes an authenticated A2A surface for hub and peer agents.
- The adapter can evolve independently without coupling external A2A clients to Compass internals.

## What This Is

- An A2A server for Compass-oriented capabilities
- A public agent card plus JSON-RPC and HTTP+JSON A2A endpoints
- HTTP Basic authentication bridged to Compass account credentials
- A read-focused capability layer backed by Compass `/agentic/*` exports

## Quick Start

Install the released CLI with `uv tool`:

```bash
uv tool install compass-a2a
```

Upgrade later with:

```bash
uv tool upgrade compass-a2a
```

Then start `compass-a2a` against your Compass API:

```bash
A2A_HOST=0.0.0.0 \
A2A_PORT=8000 \
A2A_PUBLIC_URL=https://your-domain.example.com/compass-a2a \
A2A_COMPASS_API_BASE_URL=https://your-domain.example.com/api/v1 \
compass-a2a
```

`A2A_COMPASS_API_BASE_URL` should point to the upstream Compass API used for
login, token exchange, and capability dispatch.

Verify that the service is up:

```bash
curl http://127.0.0.1:8000/.well-known/agent-card.json
curl http://127.0.0.1:8000/healthz
```

Common runtime settings:

- `A2A_HOST`
- `A2A_PORT`
- `A2A_PUBLIC_URL`
- `A2A_COMPASS_API_BASE_URL`

Optional token cache tuning:

- `A2A_TOKEN_CACHE_TTL_SECONDS`
- `A2A_TOKEN_CACHE_REFRESH_SKEW_SECONDS`
- `A2A_TOKEN_CACHE_MAX_ENTRIES`

## Authentication

Inbound runtime access uses HTTP Basic authentication.

- The Basic Auth username and password are treated as Compass login credentials.
- The adapter does not maintain a separate user system.
- The authenticated Compass principal is reused for later Compass-facing calls.
- Compass-owned personalization such as locale or time zone stays on the Compass side.

Access tokens are cached in memory per authenticated user, with expiration,
refresh skew, and cache size limits to avoid unbounded session growth.

## Calling The Adapter

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

For quick manual testing, slash-style read skill commands also work:

```text
/review_time_and_activity {"start_date":"2026-03-25T00:00:00Z","end_date":"2026-03-25T23:59:59Z"}
```

Current contract rules:

- `metadata.compass` must be an object when provided
- exactly one of `metadata.compass.skill` or `metadata.compass.command` may be set
- `metadata.compass.arguments` must be a JSON object
- slash-style read skill arguments must be a JSON object
- invalid capability contracts fail fast with an explicit adapter error

Plain text without `metadata.compass.*` or a slash-style command is accepted,
but it currently falls back to capability help text. The adapter does not yet
perform natural-language intent routing.

## Current Read Skills

The current public skill surface is read-only:

- `review_time_and_activity`
- `search_personal_knowledge`
- `review_planning`
- `review_finance_state`
- `review_vision_focus`

Write commands keep a separate execution path for future approval-aware
mutations, but no write commands are enabled yet.

## Public Surface

Public endpoints:

- `GET /.well-known/agent-card.json`
- `GET /.well-known/agent.json`
- `GET /healthz`

Protected endpoints:

- `POST /`
- `POST /v1/message:send`
- `POST /v1/message:stream`
- `GET /v1/card`

The adapter advertises both `JSONRPC` and `HTTP+JSON` transports through the
agent card.

## When To Use It

Use this project when:

- you want Compass capabilities exposed through a standard A2A surface
- you want authentication to remain anchored to Compass accounts
- you want a thin adapter instead of embedding A2A concerns inside Compass

Look elsewhere if:

- you need a free-form chat relay backed by Compass chat
- you need durable session storage or long-lived task orchestration
- you need approval-enabled write workflows today
- you want hard multi-tenant isolation inside one shared runtime

## Development

Run local checks:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Build and smoke test release artifacts locally:

```bash
uv build --no-sources
bash ./scripts/smoke_test_built_cli.sh dist/compass_a2a-*.whl
bash ./scripts/smoke_test_built_cli.sh dist/compass_a2a-*.tar.gz
```

## Release

`compass-a2a` uses tag-driven releases:

- merge the release-ready commit into `master`
- create and push a version tag in the form `vX.Y.Z`
- publish only from tag commits reachable from `origin/master`
- let the publish workflow build, verify, and release the package
