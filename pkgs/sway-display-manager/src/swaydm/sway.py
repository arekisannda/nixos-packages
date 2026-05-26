import json
import threading
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from pprint import pformat
from typing import Callable, List, Optional, Set

from i3ipc import (
    BarconfigUpdateEvent,
    Connection,
    Event,
    OutputEvent,
    OutputReply,
)

from . import config, profile, utils
from .code import Code
from .datatypes import FALLBACK, ApplyOutput, ApplyProfile, Config

OK, ERROR = (Code.OK, Code.ERROR)


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
class DisplayManager:
    config_loader: Callable[[Path], Config]
    config: Config = field(default_factory=Config)
    ipc: Connection = field(default_factory=Connection)
    current_profile: Optional[str] = None
    _config_file_path: Optional[str] = None
    _profile_set: Set = field(default_factory=set)
    _output_set: Set = field(default_factory=set)
    _auto: bool = True

    def toggle_auto_apply(self) -> None:
        self._auto = not self._auto

    def is_active(self) -> bool:
        return self._auto

    def update_profile_map(self) -> None:
        self._profile_set.clear()
        self._profile_set = {p.name for p in self.config.profiles}

    def is_profile_valid(self, target_profile: str) -> Optional[str]:
        return target_profile in self._profile_set

    def load_config(self, config_file_path: Path) -> None:
        self._config_file_path = config_file_path
        self.config = self.config_loader(self._config_file_path)
        self.update_profile_map()

    def reload_config(self) -> None:
        self.load_config(self._config_file_path)

    def update_output_state(self, output_state: List[OutputReply]) -> None:
        self._output_set.clear()
        self._output_set = {o.name for o in output_state}

    def is_output_set_changed(self, output_state: List[OutputReply]) -> bool:
        new_output_set = {o.name for o in output_state}
        return new_output_set != self._output_set


mgr: DisplayManager = DisplayManager(config_loader=config.load_config)

_apply_lock = threading.Lock()


def on_output_event(ipc: Connection, event: OutputEvent) -> None:
    utils.trace(f"handling {event.ipc_data}")

    if mgr.is_output_set_changed(ipc.get_outputs()):
        # list of output devices has changed
        utils.debug("output event detected addition/removal of outputs")
        utils.debug(f"previous profile {mgr.current_profile!r} ==> None")
        mgr.current_profile = None
        return apply_profile_auto_select()


def apply_profile_fallback() -> None:
    req_id = uuid.uuid4()
    with _apply_lock:
        utils.trace("apply fallback profile")
        apply_profile(req_id, mgr.ipc, Config(), target_profile_name=FALLBACK)
        utils.trace(f"--{req_id} completed--")


def apply_profile_auto_select() -> None:
    req_id = uuid.uuid4()
    with _apply_lock:
        utils.trace("apply auto-select profile")
        apply_profile(
            req_id, mgr.ipc, mgr.config, target_profile_name=mgr.current_profile
        )
        utils.trace(f"--{req_id} completed--")


def apply_profile_target(target_profile_name: str) -> None:
    req_id = uuid.uuid4()
    with _apply_lock:
        utils.trace(f"apply {target_profile_name}")
        apply_profile(
            req_id, mgr.ipc, mgr.config, target_profile_name=target_profile_name
        )
        utils.trace(f"--{req_id} completed--")


def apply_profile(
    uuid: uuid.UUID,
    ipc: Connection,
    config: Config,
    target_profile_name: Optional[str],
) -> None:
    if not mgr.is_active():
        utils.debug("Display manager auto-apply is paused")
        return

    utils.trace(f"-------------------{uuid} start --------------------------")
    outputs: List[OutputReply] = mgr.ipc.get_outputs()

    if target_profile_name is FALLBACK:
        utils.debug(f"{target_profile_name!r} is the fallback profile")
        config = Config()
    else:
        # check if current_profile still exists in config
        if not mgr.is_profile_valid(target_profile_name):
            utils.debug(
                f"{target_profile_name!r} is not in the list of available profiles. switching to auto-selected profile"
            )
            target_profile_name = None

    target_profile: ApplyProfile = profile.get_profile(
        config, outputs, target_profile_name
    )

    if (
        target_profile_name
        and target_profile_name != FALLBACK
        and target_profile.name == FALLBACK
    ):
        raise RuntimeError(f"{target_profile_name!r} cannot be configured")

    output_by_name = {o.name: o for o in outputs}

    for apply in target_profile.outputs:
        utils.trace(f"checking {apply.name}")
        current = output_by_name.get(apply.name)
        if current and profile.is_output_already_configured(current, apply):
            utils.debug(
                f"{target_profile.name!r}: {apply.name!r} is already the desired state, skip"
            )
            continue

        if apply.active:
            m, p = apply.mode, apply.position
            commands = (
                f"output {apply.name} enable "
                f"mode {m.width}x{m.height}@{m.refresh}Hz scale {m.scale} "
                f"position {p.x} {p.y} "
            )

            utils.trace(f"command => {commands}")
            ipc.command(commands)
        else:
            utils.trace(f"command => output {apply.name} disable")
            ipc.command(f"output {apply.name} disable")

    utils.info(f"Current profile: {target_profile.name}")
    utils.trace(f"profile layout {target_profile.outputs}")

    alias_to_output_name = {
        apply.alias: apply.name
        for apply in target_profile.outputs
        if apply.alias
    }
    utils.trace(f"aliases: {alias_to_output_name}")

    if target_profile.commands:
        utils.trace(f"Run {target_profile_name!r} additional commands")
        for ind, cmd in enumerate(target_profile.commands):
            cmd = cmd.format_map(alias_to_output_name)
            utils.trace(f"command => {ind}:{cmd}")
            ipc.command(cmd)

    mgr.update_output_state(mgr.ipc.get_outputs())
    mgr.current_profile = target_profile.name
    utils.trace(f"-------------------{uuid} end --------------------------")


def command_resp(
    resp_code: Code,
    msg: str,
) -> str:
    return f"{resp_code}\n{msg}"


def command_handler(command: str) -> str:
    parts = command.split()
    if not parts:
        return "error: empty command"

    match parts[0]:
        case "toggle_auto_apply":
            utils.info("Toggle display manager auto")
            mgr.toggle_auto_apply()
            apply_profile_auto_select()
            if mgr.is_active():
                return command_resp(OK, "Auto-apply resumed")
            else:
                return command_resp(OK, "Auto-apply paused")

        case "reload":
            utils.info("Reloading configurations")
            mgr.reload_config()
            apply_profile_auto_select()
            return command_resp(OK, "Configuration reloaded")

        case "list_profiles":
            return command_resp(
                OK, f"{'\n'.join([p.name for p in mgr.config.profiles])}"
            )

        case "status" | "status_json":
            current_profile = profile.get_profile(
                mgr.config, mgr.ipc.get_outputs(), mgr.current_profile
            )

            output_info = StatusOutput(
                active=mgr.is_active(),
                profile=mgr.current_profile,
                layout=current_profile.outputs,
                current_config=mgr.config,
            )

            verbose = len(parts) >= 2 and parts[1] == "verbose"
            match parts[0]:
                case "status":
                    return command_resp(OK, output_info.format(verbose))
                case "status_json":
                    return command_resp(OK, output_info.format_json(verbose))

        case "switch_profile":
            if len(parts) < 2:
                return command_resp(ERROR, "usage: switch <profile>")

            profile_name = parts[1]
            utils.info(f"Switching profile to {profile_name}")

            if profile_name == FALLBACK:
                apply_profile_fallback()
                return command_resp(OK, f"Switched to {FALLBACK!r}")

            if not mgr.is_profile_valid(profile_name):
                utils.warning(f"{profile_name!r} is not a valid profile.")
                return command_resp(
                    ERROR, f"{profile_name!r} is not a valid profile."
                )
            try:
                apply_profile_target(profile_name)
            except RuntimeError as e:
                utils.warning(f"Failed to apply profile: {e}")
                return command_resp(
                    ERROR, f"Unable to switch to {profile_name!r}"
                )
            return command_resp(OK, f"Switched to {profile_name!r}")

        case _:
            return command_resp(ERROR, f"error: unknown command {parts[0]!r}")


def on_config_reload_event(
    ipc: Connection, event: BarconfigUpdateEvent
) -> None:
    utils.trace("handling Sway configuration reload event")
    apply_profile_auto_select()


def start_watcher(config_file_path: Path) -> None:
    mgr.load_config(config_file_path)
    mgr.ipc.on(Event.BARCONFIG_UPDATE, on_config_reload_event)
    mgr.ipc.on(Event.OUTPUT, on_output_event)
    mgr.update_output_state(mgr.ipc.get_outputs())

    apply_profile_auto_select()

    utils.debug(f"Starting Sway output watcher {str(config_file_path)!r}")
    mgr.ipc.main()
