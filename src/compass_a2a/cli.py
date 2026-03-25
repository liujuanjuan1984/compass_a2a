import uvicorn

from .config import Settings


def main() -> int:
    settings = Settings()
    if settings.public_url is None:
        settings.public_url = f"http://{settings.host}:{settings.port}"

    uvicorn.run(
        "compass_a2a.app:build_app",
        factory=True,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
