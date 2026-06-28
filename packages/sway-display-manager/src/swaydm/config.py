import os
from pathlib import Path
from typing import Optional

import yaml

from . import utils
from .datatypes import FALLBACK, Config, Display, Mode, Position, Profile

DEFAULT_CONFIG_FILES = [
    "$XDG_CONFIG_HOME/swaydm/config.yaml",
    "$XDG_CONFIG_HOME/swaydm.yaml",
]


def parse_display(d: dict) -> Display:
    return Display(
        name=d["name"],
        alias=d["alias"] if "alias" in d else None,
        mode=Mode(**d["mode"]) if "mode" in d else None,
        position=Position(**d["position"]) if "position" in d else None,
    )


def parse_profile(d: dict) -> Profile:
    if d["name"] == FALLBACK:
        raise ValueError(f"profile name {FALLBACK!r} is reserved")

    return Profile(
        name=d["name"],
        auto=d.get("auto", True),
        displays=[parse_display(d) for d in d.get("displays", [])],
        commands=d.get("commands", []),
    )


def find_config_file(target: str) -> Optional[Path]:
    candidates = ([target] if target else []) + DEFAULT_CONFIG_FILES

    for c in candidates:
        config_path = Path(os.path.expandvars(os.path.expanduser(c)))
        if config_path.is_file():
            utils.debug(f"Using configuration file at {str(config_path)!r}")
            return config_path

    utils.debug("Using fallback configurations")
    return None


def load_config(path: Optional[Path]) -> Config:
    utils.trace(f"load configuration from {str(path)!r}")
    if not path or not path.is_file():
        return Config()

    with open(path, 'r') as f:
        data = yaml.safe_load(f)

    if not data:
        return Config()

    return Config(
        profiles=[
            parse_profile(profile) for profile in data.get("profiles", [])
        ],
    )
