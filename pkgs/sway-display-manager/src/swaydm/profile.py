from typing import List, Optional

from i3ipc import OutputReply

from . import utils
from .datatypes import (
    ApplyProfile,
    ApplyOutput,
    Config,
    Profile,
    Mode,
    Position,
    FALLBACK,
)


def is_output_already_configured(
    output: OutputReply, apply: ApplyOutput
) -> bool:
    if not apply.active:
        return not output.active

    m = apply.mode
    p = apply.position
    current_refresh_hz = round(
        (output.current_mode.refresh if output.current_mode else 0) / 1000
    )
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


def get_profile_output_mapping(
    profile: Profile, outputs: List[OutputReply]
) -> List[ApplyOutput]:
    assigned: dict[str, ApplyOutput] = {}
    used: set[str] = set()
    result: list[ApplyOutput] = []

    for ind, display in enumerate(profile.displays):
        chosen: Optional[dict] = None
        if display.mode is None:
            continue

        for output in outputs:
            if output.name in used:
                utils.trace(f"Skip {output.name} is used")
                continue
            if not matches_display_name(output, display.name):
                utils.trace(f"{display.name!r}:{ind} does not match an output")
                continue
            if display.mode is not None and not matches_display_mode(
                output, display.mode
            ):
                utils.trace(
                    f"{display.name!r}:{ind} does not match {output.name!r} mode"
                )
                continue
            chosen = output
            utils.trace(
                f"{profile.name!r} request {ind}:{display.name!r} matched {output.name!r}"
            )
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

    # Disable everything not claimed by the profile.
    for output in outputs:
        if output.name in assigned:
            result.append(assigned[output.name])
        else:
            result.append(
                ApplyOutput(name=output.name, active=False, fallback=False)
            )

    return result


def get_valid_profiles(
    cand_profiles: List[Profile], outputs: List[OutputReply]
) -> List[ApplyProfile]:
    result: List[ApplyProfile] = []

    for p in cand_profiles:
        try:
            result.append(
                ApplyProfile(
                    name=p.name,
                    outputs=get_profile_output_mapping(p, outputs),
                    commands=p.commands,
                )
            )
        except ValueError as e:
            utils.debug(f"{p.name!r} cannot be configured - {e}")
            continue

    return result


def get_profile(
    config: Config, outputs: List[OutputReply], profile: Optional[str] = None
) -> ApplyProfile:
    profiles = (
        [p for p in config.profiles if p.name == profile]
        if profile
        else [p for p in config.profiles if p.auto]
    )

    if not profiles and profile != FALLBACK:
        utils.debug(f"{profile!r} is not a profile")
        raise ValueError(f"{profile!r} is not a profile")

    valid: List[ApplyProfile] = get_valid_profiles(profiles, outputs)

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
                mode=Mode(
                    width=width, height=height, refresh=refresh, scale=1.0
                ),
                position=Position(x=current_width, y=0),
            )
        )
        current_width += width

    return ApplyProfile(name=FALLBACK, outputs=fallback_outputs, commands=[])
