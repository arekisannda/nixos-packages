import json
from dataclasses import asdict, dataclass, field
from typing import List, Optional

import yaml

from . import manager, profile, utils
from .code import Code
from .datatypes import FALLBACK, ApplyOutput, Config

OK, ERROR = (Code.OK, Code.ERROR)


@dataclass
class StatusOutput:
    active: bool
    profile: Optional[str]
    current_config: Config
    layout: List[ApplyOutput] = field(default_factory=list)

    def status(self, verbose: bool = False) -> str:
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
            f"Profile: {self.profile if self.profile else ''}",
            f"Layout: {''.join(layout)}",
        ]

        if verbose:
            lines.append("\nProfiles:")
            lines.append(
                yaml.dump(
                    asdict(self.current_config).get('profiles', []),
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )
            )

        return "\n".join(lines)

    def status_json(self, verbose: bool = False) -> str:
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


def command_resp(
    resp_code: Code,
    msg: str,
) -> str:
    return f"{resp_code}\n{msg}"


def switch_profile(profile_name: str) -> str:
    utils.info(f"Switching profile to {profile_name!r}")

    if profile_name == FALLBACK:
        manager.apply_profile_fallback()
        return command_resp(OK, f"Switched to {profile_name!r}")

    if not manager.mgr.is_profile_valid(profile_name):
        utils.warning(f"{profile_name!r} is not a valid profile.")
        return command_resp(ERROR, f"{profile_name!r} is not a valid profile.")
    try:
        manager.apply_profile_target(profile_name)
    except RuntimeError as e:
        utils.warning(f"Failed to apply profile: {e}")
        return command_resp(ERROR, f"Unable to switch to {profile_name!r}")
    return command_resp(OK, f"Switched to {profile_name!r}")


def command_handler(command: str) -> str:
    parts = command.split()
    if not parts:
        return "error: empty command"

    match parts[0]:
        case "toggle_auto_apply" | "enable_auto_apply" | "disable_auto_apply":
            getattr(manager.mgr, parts[0])()
            if manager.mgr.is_active():
                manager.apply_profile_auto_select()
                return command_resp(OK, "Auto-apply resumed")
            else:
                return command_resp(OK, "Auto-apply paused")

        case "reload":
            utils.info("Reloading configurations")
            manager.mgr.reload_config()
            manager.apply_profile_auto_select()
            return command_resp(OK, "Configuration reloaded")

        case "list_profiles":
            profile_options: List[str] = [
                p.name
                for p in profile.get_valid_profiles(
                    manager.mgr.config.profiles, manager.mgr.ipc.get_outputs()
                )
            ]

            return command_resp(OK, f"{'\n'.join(profile_options)}")

        case "status" | "status_json":
            current_profile = profile.get_profile(
                manager.mgr.config,
                manager.mgr.ipc.get_outputs(),
                manager.mgr.current_profile,
            )

            output_info = StatusOutput(
                active=manager.mgr.is_active(),
                profile=manager.mgr.current_profile,
                layout=current_profile.outputs,
                current_config=manager.mgr.config,
            )

            verbose = len(parts) >= 2 and parts[1] == "verbose"
            return command_resp(OK, getattr(output_info, parts[0])(verbose))

        case "switch_profile":
            if len(parts) < 2:
                return command_resp(ERROR, "usage: switch <profile>")
            return switch_profile(parts[1])

    return command_resp(ERROR, f"error: unknown command {parts[0]!r}")
