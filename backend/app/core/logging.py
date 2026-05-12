from __future__ import annotations

import logging
from logging.config import dictConfig

from app.core.config import Settings


def configure_logging(settings: Settings) -> None:
    log_level = "DEBUG" if settings.app_debug else "INFO"

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s %(levelname)s [%(name)s] %(message)s",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                }
            },
            "root": {
                "level": log_level,
                "handlers": ["console"],
            },
        }
    )

    logging.getLogger(__name__).debug("Logging configured for environment: %s", settings.app_env)
