"""Access the small RoboTwin configuration files shipped in the wheel."""

from __future__ import annotations

from copy import deepcopy
from importlib.resources import files
from typing import Any

import yaml

_TASK_CONFIG_PACKAGE = "robotwin.configs.task"


def _config_name(name: str) -> str:
    value = name.removesuffix(".yaml").removesuffix(".yml")
    if not value or "/" in value or "\\" in value or value in {".", ".."}:
        raise ValueError(f"invalid RoboTwin task config name: {name!r}")
    return f"{value}.yml"


def load_task_config(name: str) -> dict[str, Any]:
    """Load one packaged RoboTwin task/configuration YAML by stem."""
    resource = files(_TASK_CONFIG_PACKAGE).joinpath(_config_name(name))
    if not resource.is_file():
        raise ValueError(f"RoboTwin task config is not packaged: {name!r}")
    with resource.open("r", encoding="utf-8") as stream:
        value = yaml.safe_load(stream)
    if not isinstance(value, dict):
        raise TypeError(f"RoboTwin task config must contain a mapping: {name!r}")
    return deepcopy(value)


__all__ = ["load_task_config"]
