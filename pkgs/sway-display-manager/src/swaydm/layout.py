from typing import List, Optional

from i3ipc import OutputReply

from . import utils
from .schema import ApplyLayout, Config, Layout, Mode, Position


def is_output_already_configured(output: OutputReply, apply: ApplyLayout) -> bool:
    if not apply.active:
        return not output.active
    if not output.active:
        return False
    m = apply.mode
    p = apply.position
    current_refresh_hz = round((output.current_mode.refresh if output.current_mode else 0) / 1000)
    return (
        output.rect.x == p.x
        and output.rect.y == p.y
        and output.current_mode is not None
        and output.current_mode.width == m.width
        and output.current_mode.height == m.height
        and abs(current_refresh_hz - m.refresh) <= 1
        and output.scale == m.scale
    )


def output_identifier(output: OutputReply) -> str:
    make = output.make.strip()
    model = output.model.strip()
    serial = output.serial.strip()
    if make and model and serial:
        return f"{make} {model} {serial}"
    return output.name


def matches_display_name(output: OutputReply, display_name: str) -> bool:
    if display_name == output.name:
        return True
    if display_name == output_identifier(output):
        return True
    return False


def matches_display_mode(output: OutputReply, want: Mode) -> bool:
    for m in output.modes or []:
        if m.width != want.width or m.height != want.height:
            continue
        refresh_hz = round(m.refresh / 1000)
        if abs(refresh_hz - want.refresh) <= 1:
            return True
    return False 


def get_layout_output_mapping(layout: Layout, outputs: List[OutputReply]) -> List[ApplyLayout]:
    assigned: dict[str, ApplyLayout] = {}
    used: set[str] = set()
    result: list[ApplyLayout] = []

    for ind, display in enumerate(layout.displays):
        chosen: Optional[dict] = None
        if display.mode is None:
            continue

        for output in outputs:
            if output.name in used:
                utils.debug(f"{__name__} - Skip {output.name} is used")
                continue
            if not matches_display_name(output, display.name):
                utils.debug(f"{__name__} - {display.name}:{ind} does not match an output")
                continue
            if display.mode is not None and not matches_display_mode(output, display.mode):
                utils.debug(f"{__name__} - {display.name}:{ind} does not match {output.name} mode")
                continue
            chosen = output
            utils.debug(f"{__name__} - {display.name}:{ind} match {output.name}")
            break

        if chosen is None:
            utils.debug(f"{__name__} - {layout.name} cannot be configured")
            raise ValueError(
                f"No sway output matches display {display.name!r} "
                f"with the requested mode"
            )

        used.add(chosen.name)
        assigned[chosen.name] = ApplyLayout(
            name=chosen.name,
            active=True,
            fallback=False,
            mode=display.mode,
            position=display.position,
        )

    # Disable everything not claimed by the layout.
    for output in outputs:
        if output.name in assigned:
            result.append(assigned[output.name])
        else:
            result.append(ApplyLayout(name=output.name, active=False, fallback=False))

    return result


def get_layout(config: Config, outputs: List[OutputReply]) -> tuple[str, List[ApplyLayout]]:
    valid: List[tuple[str, List[ApplyLayout]]] = []

    for layout in config.layouts:
        try:
            valid.append((layout.name, get_layout_output_mapping(layout, outputs)))
        except ValueError as e:
           continue 
        # print(f"[Basic] Caught: {e}")

    if valid:
        return valid[0]

    fallback_layout: List[ApplyLayout] =[]
    current_width = 0
    for output in outputs:
        width = output.modes[0].width
        height = output.modes[0].height
        refresh = round(output.modes[0].refresh / 1000)
        fallback_layout.append(
            ApplyLayout(
                name=output.name,
                active=True,
                fallback=True,
                mode=Mode(width=width,
                          height=height,
                          refresh=refresh,
                          scale=1.0),
                position=Position(x=current_width, y=0)
            ))
        current_width += width

    return ("FALLBACK", fallback_layout)

