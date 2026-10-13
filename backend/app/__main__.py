"""Entry point: `python -m app`. Runs Uvicorn with JSON logging on 0.0.0.0:8000."""

import os

import uvicorn

from app.config import Settings
from app.logs import setup_logging
from app.main import create_app


def main() -> None:
    settings = Settings.from_env()
    setup_logging(settings.log_level)
    uvicorn.run(
        create_app(settings),
        host="0.0.0.0",  # noqa: S104 - inside the container; Compose decides what is exposed
        port=int(os.environ.get("PORT", "8000")),
        log_config=None,
        access_log=False,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )


if __name__ == "__main__":
    main()
