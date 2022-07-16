# Copyright (C) 2019-2022, François-Guillaume Fernandez.

# This program is licensed under the Apache License 2.0.
# See LICENSE or go to <https://www.apache.org/licenses/LICENSE-2.0> for full license details.


import os
from pathlib import Path

from packaging import parse
from setuptools import setup

PKG_NAME = "pylocron"
VERSION = os.getenv("BUILD_VERSION", "0.2.2.dev0")


if __name__ == "__main__":

    version_index = str(parse(VERSION))
    print(f"Building wheel {PKG_NAME}-{version_index}")

    # Dynamically set the __version__ attribute
    cwd = Path(__file__).parent.absolute()
    with open(cwd.joinpath("holocron", "version.py"), "w", encoding="utf-8") as f:
        f.write(f"__version__ = '{version_index}'\n")

    setup(name=PKG_NAME, version=version_index)
