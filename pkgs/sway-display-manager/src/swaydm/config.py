import yaml

from .schema import Config, Display, Layout, Mode, Position


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


def load_config(path: str) -> Config:
    with open(path, 'r') as f:
        data = yaml.safe_load(f)

    return Config(
        layouts=[parse_layout(layout) for layout in data.get("layouts", [])],
    )
