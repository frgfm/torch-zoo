# Copyright (C) 2022-2023, François-Guillaume Fernandez.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.

import os

from pydantic_settings import BaseSettings

__all__ = ["settings"]


class Settings(BaseSettings):
    # State
    PROJECT_NAME: str = "Holocron API template"
    PROJECT_DESCRIPTION: str = "Template API for Computer Vision"
    VERSION: str = "0.2.2.dev0"
    DEBUG: bool = os.environ.get("DEBUG", "") != "False"
    CLF_HUB_REPO: str = os.environ.get("CLF_HUB_REPO", "frgfm/rexnet1_5x")


settings = Settings()
