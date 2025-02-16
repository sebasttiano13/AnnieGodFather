# -*- coding: utf-8 -*-

import logging

from dynaconf import Dynaconf
from pydantic import BaseModel, field_validator

# Load envs
settings = Dynaconf(load_dotenv=True, envvar_prefix="GODFATHER")


class AppConfig(BaseModel):
    LOG_LEVEL: str = "INFO"
    TELEGRAM_TOKEN: str
    LOG_FILE: str = None

    @field_validator("LOG_LEVEL")
    def check_log_level(cls, value):
        log_levels = logging._nameToLevel.keys()
        if value not in log_levels:
            raise ValueError("Invalid log level: %s. Available log levels: %s" % (value, log_levels))
        return value


config = AppConfig(**settings.as_dict())