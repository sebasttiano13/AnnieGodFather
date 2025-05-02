# -*- coding: utf-8 -*-

import logging
import logging.config
from settings import config


class LogHandler(logging.Handler):
    """This is a handler that writes logs to a file"""

    def __init__(self, filename: str):
        logging.Handler.__init__(self)
        self.filename = filename

    def emit(self, record: logging.LogRecord):
        """
        This method directly performs the action with the log.
        The LogRecord object is passed to it
        """

        message = self.format(record)
        with open(self.filename, "a", encoding="utf-8") as file:
            file.write(message + "\n")


# Module logging config
logger_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "std_format": {
            "format": "{asctime} - {levelname} - {name} - {message}",
            "style": "{",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": config.LOG_LEVEL,
            "formatter": "std_format",
        },
        "filesave": {
            # Class init
            "()": LogHandler,
            "level": config.LOG_LEVEL,
            "filename": f"{config.LOG_FILE}",
            "formatter": "std_format",
        },
    },
    "loggers": {
        "anniegodfather-logger": {"level": config.LOG_LEVEL, "handlers": ["console"]},
    },
}

logging.config.dictConfig(logger_config)
logger = logging.getLogger("anniegodfather-logger")
