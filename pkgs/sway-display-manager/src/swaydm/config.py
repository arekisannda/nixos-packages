import os
from pathlib import Path
from typing import Optional

import yaml

from .schema import Config, Display, Layout, Mode, Position
from . import utils

DEFAULT_CONFIG_FILES = [
    "$XDG_CONFIG_HOME/swaydm/config.yaml",
    "$XDG_CONFIG_HOME/swaydm.yaml"
]


def parse_display(d: dict) -> Display:
    return Display(
        name=d["name"],
        alias = d["alias"] if "alias" in d else None,
        mode=Mode(**d["mode"]) if "mode" in d else None,
        position=Position(**d["position"]) if "position" in d else None,
    )


def parse_layout(d: dict) -> Layout:
    return Layout(
        name=d["name"],
        displays=[parse_display(d) for d in d.get("displays", [])],
        commands=d.get("commands", []),
    )


def find_config_file(target: str) -> Optional[Path]:
    candidates = ([target] if target else []) + DEFAULT_CONFIG_FILES

    for c in candidates:
        config_path = Path(os.path.expandvars(os.path.expanduser(target)))
        if config_path.is_file():
            utils.debug(f"Using configuration file at {config_path}")
            return config_path

    utils.debug("Using fallback configurations")
    return None


def load_config(path: Path) -> Config:
    if not path or not path.is_file():
        return Config()

    with open(path, 'r') as f:
        data = yaml.safe_load(f)

    if not data:
        return Config()

    return Config(
        layouts=[parse_layout(layout) for layout in data.get("layouts", [])],
    )
