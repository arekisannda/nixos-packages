from dataclasses import dataclass, field
from typing import List, Optional


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
    mode: Optional[Mode] = None
    position: Optional[Position] = None


@dataclass
class Layout:
    name: str
    displays: List[Display] = field(default_factory=list)


@dataclass
class Config:
    layouts: List[Layout] = field(default_factory=list)

@dataclass
class ApplyLayout:
    name: str
    active: bool
    fallback: bool
    mode: Optional[Mode] = None
    position: Optional[Position] = None

