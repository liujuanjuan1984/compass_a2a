# compass-a2a

`compass-a2a` is the dedicated A2A adapter service for Compass.

It is intentionally positioned as a separate process boundary:

- Compass stays the source of truth for LifeOS data and domain rules.
- `compass-a2a` exposes an A2A-facing runtime surface for hub and peer agents.
- The adapter can evolve independently from Compass internals.

## Bootstrap Scope

This repository is initialized with:

- `uv` for dependency and environment management
- `pre-commit` for basic code quality checks
- a minimal A2A server surface
- a public agent card endpoint
- HTTP Basic authentication bridged to Compass account credentials

## Quick Start

Install

```bash
uv tool install compass-a2a
```

Upgrade

```bash
uv tool upgrade compass-a2a
```

Run (complete example)

```bash
 A2A_HOST=127.0.0.1 \
 A2A_PORT=8000 \
 A2A_PUBLIC_URL=http://127.0.0.1:8000 \
compass-a2a
```

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

The adapter does not inject user personalization fields such as locale or time
zone. Those preferences remain owned by Compass itself.

Access tokens are cached in memory on a per-user basis, but they are no longer
treated as unbounded session state. The adapter now applies token expiration,
refresh skew, and cache size limits so expired or cold entries are recycled.

Optional cache tuning env vars:

- `A2A_TOKEN_CACHE_TTL_SECONDS`
- `A2A_TOKEN_CACHE_REFRESH_SKEW_SECONDS`
- `A2A_TOKEN_CACHE_MAX_ENTRIES`

## Capability Model

The current branch keeps a deliberate split between read skills and write
commands.

- Read skills are the current public capability surface.
- Write commands are reserved for approval-aware mutations and have a separate
  execution path, even though no write commands are enabled yet.

The current bootstrap skill catalog internally uses Compass `/agentic/*` facade
endpoints as the initial data source.

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

Contract rules for capability requests:

- `metadata.compass` must be an object when provided
- exactly one of `metadata.compass.skill` or `metadata.compass.command` may be set
- `metadata.compass.arguments` must be a JSON object
- slash-style read skill arguments must also be a JSON object
- invalid capability contracts fail fast with an explicit adapter error instead of silently falling back to help text

Future write commands will use a separate metadata field:

```json
{
  "compass": {
    "command": "create_note",
    "arguments": {
      "title": "Draft"
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
Compass itself, so `compass-a2a` remains a thin protocol and policy layer.

## Development

Run checks:

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

`compass-a2a` uses tag-driven releases.

- Merge the release-ready commit into `master`
- Create and push a version tag in the form `vX.Y.Z`
- The publish workflow will only proceed when the tag commit is reachable from `origin/master`
- The workflow builds artifacts, verifies that the package version matches the tag, publishes to PyPI, and creates a GitHub Release

PyPI publishing is configured for GitHub OIDC trusted publishing. The PyPI
project must trust this repository and the `publish.yml` workflow before the
first release can succeed.

## Roadmap

This bootstrap intentionally keeps the runtime thin. The next steps are expected
to include:

- Compass API integration
- approval-aware write operations
- richer task execution and streaming behavior
- durable task/session storage
