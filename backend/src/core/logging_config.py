import logging
import logging.config

logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"},
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
            "level": "DEBUG",
            "filename": "logs/app.log",
            "maxBytes": 10_000_000,
            "backupCount": 5,
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "DEBUG",
    },
}


def setup_logging():
    logging.config.dictConfig(logging_config)
