from dataclasses import dataclass, field
from typing import List, Optional

FALLBACK = "default"


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
    auto: bool = True
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
