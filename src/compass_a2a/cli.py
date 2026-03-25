from __future__ import annotations

import argparse

import uvicorn

from .config import Settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="compass-a2a",
        description="Run the compass-a2a adapter service.",
    )
    parser.add_argument("--host", help="Host override.")
    parser.add_argument("--port", type=int, help="Port override.")
    parser.add_argument("--reload", action="store_true", help="Enable autoreload.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    settings = Settings()
    uvicorn.run(
        "compass_a2a.app:build_app",
        factory=True,
        host=args.host or settings.host,
        port=args.port or settings.port,
        reload=args.reload,
        log_level=settings.log_level.lower(),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
