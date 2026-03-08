import logging
import logging.config
import os

LOG_PATH = os.path.join(os.path.dirname(__file__), "../../logs/app.log")

_logging_configured = False


def setup_logging(log_level: str = "INFO"):
    """
    Configure the root logger with console and rotating file handlers.

    Idempotent: subsequent calls are no-ops, so it is safe to import this
    module from multiple places without reconfiguring logging.

    Args:
        log_level: Logging level name (e.g. "DEBUG", "INFO", "WARNING").
                   Defaults to "INFO".
    """
    # check for setup rerun
    global _logging_configured
    if _logging_configured:
        return

    # logging configuration
    log_level = log_level.upper()
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "level": "DEBUG",
                "stream": "ext://sys.stdout",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "standard",
                "level": log_level,
                "filename": LOG_PATH,
                "maxBytes": 10_000_000,
                "backupCount": 5,
            },
        },
        "root": {
            "handlers": ["console", "file"],
            "level": log_level,
        },
    }
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    logging.config.dictConfig(logging_config)
    _logging_configured = True


def redirect_uvicorn_loggers():
    """
    Route uvicorn logs through the root logger.

    Uvicorn configures its own handlers with propagate=False on startup,
    so its logs bypass the root logger and never reach the file handler.
    This function clears those handlers and re-enables propagation so all
    uvicorn log records flow through the configured root logger instead.

    Must be called after uvicorn has finished its own logging setup,
    e.g. inside the FastAPI lifespan.
    """
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True
