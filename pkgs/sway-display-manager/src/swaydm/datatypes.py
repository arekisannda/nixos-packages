import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from pprint import pformat
from typing import Callable, List, Optional

from i3ipc import Connection

FALLBACK = "FALLBACK"


@dataclass
class Mode:
    width: int
    height: int
    refresh: int
    scale: float


@dataclass
class Position:
    x: int
    y: int


@dataclass
class Display:
    name: str
    alias: Optional[str] = None
    mode: Optional[Mode] = None
    position: Optional[Position] = None


@dataclass
class Profile:
    name: str
    displays: List[Display] = field(default_factory=list)
    commands: List[str] = field(default_factory=list)


@dataclass
class Config:
    profiles: List[Profile] = field(default_factory=list)


@dataclass
class ApplyOutput:
    name: str
    active: bool
    fallback: bool
    alias: Optional[str] = None
    mode: Optional[Mode] = None
    position: Optional[Position] = None


@dataclass
class ApplyProfile:
    name: str
    outputs: List[ApplyOutput] = field(default_factory=list)
    commands: List[str] = field(default_factory=list)


@dataclass
class StatusOutput:
    active: bool
    profile: str
    current_config: Config
    layout: List[ApplyOutput] = field(default_factory=list)

    def format(self, verbose: bool = False) -> str:
        layout = [
            (
                f"\n{p.name!r}\t"
                f"{p.mode.width}x{p.mode.height}@{p.mode.refresh}Hz "
                f"({p.position.x},{p.position.y})"
            )
            if p.mode and p.position
            else f"\n{p.name!r} disabled"
            for p in self.layout
        ]

        lines = [
            f"Active: {'yes' if self.active else 'no'}",
            f"Profile: {self.profile}",
            f"Layout: {''.join(layout)}",
        ]

        if verbose:
            lines.append(
                pformat(asdict(self.current_config), width=1, sort_dicts=False)
            )
        return "\n".join(lines)

    def format_json(self, verbose: bool = False) -> str:
        layout = {
            p.name: {
                'mode': f"{p.mode.width}x{p.mode.height}@{p.mode.refresh}Hz",
                'position': f"{p.position.x},{p.position.y}",
            }
            if p.mode and p.position
            else None
            for p in self.layout
        }
        json_out = {
            'active': self.active,
            'profile': self.profile,
            'layout': layout,
        }

        if verbose:
            json_out['config'] = asdict(self.current_config)

        return json.dumps(json_out, indent=2, default=str)


@dataclass
class IPCManager:
    socket: str


@dataclass
class DisplayManager:
    config_loader: Callable[[Path], Config]
    config: Config = field(default_factory=Config)
    ipc: Connection = field(default_factory=Connection)
    current_profile: Optional[str] = None
    _config_file_path: Optional[str] = None
    _profile_map: dict[str, Profile] = field(default_factory=dict)
    _auto: bool = True

    def toggle_auto_apply(self) -> None:
        self._auto = not self._auto

    def is_active(self) -> bool:
        return self._auto

    def update_profile_map(self) -> None:
        self._profile_map.clear()
        self._profile_map = {p.name: p for p in self.config.profiles}

    def get_profile(self, target_profile: str) -> Optional[str]:
        return self._profile_map.get(target_profile, None)

    def load_config(self, config_file_path: Path) -> None:
        self._config_file_path = config_file_path
        self.config = self.config_loader(self._config_file_path)
        self.update_profile_map()

    def reload_config(self) -> None:
        self.load_config(self._config_file_path)
