"""Logging to the console in a way Railway understands.

Railway marks everything written to stderr as an error. Informational
messages therefore go to stdout and only warnings and errors to stderr.
"""

import logging

FORMAT = "[%(asctime)s] [%(process)d] [%(levelname)s] %(name)s: %(message)s"
# gunicorn's logger is called "gunicorn.error" even for INFO lines – leave the name out.
GUNICORN_FORMAT = "[%(asctime)s] [%(process)d] [%(levelname)s] %(message)s"


class BelowWarning(logging.Filter):
    def filter(self, record):
        return record.levelno < logging.WARNING


def handlers():
    return {
        "stdout": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "filters": ["below_warning"],
            "formatter": "default",
        },
        "stderr": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
            "level": "WARNING",
            "formatter": "default",
        },
    }


def logging_config(level="INFO", loggers=None, fmt=FORMAT):
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {"below_warning": {"()": "config.log_config.BelowWarning"}},
        "formatters": {"default": {"format": fmt}},
        "handlers": handlers(),
        "root": {"handlers": ["stdout", "stderr"], "level": level},
        "loggers": loggers or {},
    }
