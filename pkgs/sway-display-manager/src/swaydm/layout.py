from typing import List, Optional

from i3ipc import OutputReply

from . import utils
from .schema import ApplyLayout, ApplyOutput, Config, Layout, Mode, Position


def is_output_already_configured(output: OutputReply, apply: ApplyOutput) -> bool:
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


def get_layout_output_mapping(layout: Layout, outputs: List[OutputReply]) -> List[ApplyOutput]:
    assigned: dict[str, ApplyOutput] = {}
    used: set[str] = set()
    result: list[ApplyOutput] = []

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
            raise ValueError(
                f"No sway output matches display {display.name!r} "
                f"with the requested mode"
            )

        used.add(chosen.name)
        assigned[chosen.name] = ApplyOutput(
            name=chosen.name,
            alias=display.alias,
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
            result.append(ApplyOutput(name=output.name, active=False, fallback=False))

    return result


def get_layout(config: Config, outputs: List[OutputReply], target: Optional[str] = None) -> ApplyLayout:
    valid: List[ApplyLayout] = []

    layouts = [cl for cl in config.layouts if cl.name == target] if target else config.layouts

    if not layouts and target:
        utils.debug(f"\"{target}\" is not a layout profile")
        raise ValueError(
            f"\"{target}\" is not a layout profile"
        )

    for layout in layouts:
        try:
            valid.append(ApplyLayout(
                name=layout.name,
                outputs=get_layout_output_mapping(layout, outputs),
                commands=layout.commands
            ))
        except ValueError as e:
            utils.debug(f"{layout.name} cannot be configured - {e}")
            continue 

    if valid:
        return valid[0]

    fallback_outputs: List[ApplyOutput] = []
    current_width = 0
    for output in outputs:
        width = output.modes[0].width
        height = output.modes[0].height
        refresh = round(output.modes[0].refresh / 1000)
        fallback_outputs.append(
            ApplyOutput(
                name=output.name,
                alias=None,
                active=True,
                fallback=True,
                mode=Mode(width=width,
                          height=height,
                          refresh=refresh,
                          scale=1.0),
                position=Position(x=current_width, y=0)
            ))
        current_width += width

    return ApplyLayout(
        name="FALLBACK",
        outputs=fallback_outputs,
        commands=[]
    )

