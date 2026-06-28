import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Set

from i3ipc import Connection, Event, OutputReply
from i3ipc.events import IpcBaseEvent

from . import config, profile, utils
from .datatypes import FALLBACK, ApplyProfile, Config


@dataclass
class ManagerState:
    config_loader: Callable[[Optional[Path]], Config]
    config: Config = field(default_factory=Config)
    ipc: Connection = field(default_factory=Connection)
    current_profile: Optional[str] = None
    _config_file_path: Optional[Path] = None
    _profile_set: Set = field(default_factory=set)
    _output_set: Set = field(default_factory=set)
    _auto: bool = True

    def toggle_auto_apply(self) -> None:
        self._auto = not self._auto

    def enable_auto_apply(self) -> None:
        self._auto = True

    def disable_auto_apply(self) -> None:
        self._auto = False

    def is_active(self) -> bool:
        return self._auto

    def update_profile_map(self) -> None:
        self._profile_set.clear()
        self._profile_set = {p.name for p in self.config.profiles}

    def is_profile_valid(self, target_profile: str) -> bool:
        return target_profile in self._profile_set

    def load_config(self, config_file_path: Optional[Path]) -> None:
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


mgr: ManagerState = ManagerState(config_loader=config.load_config)

_apply_lock = threading.Lock()


def on_output_event(ipc: Connection, _event: IpcBaseEvent) -> None:
    if not mgr.is_active():
        utils.debug("Display manager auto-apply is paused")
        return

    utils.trace("handling output event")

    with _apply_lock:
        if mgr.is_output_set_changed(ipc.get_outputs()):
            # list of output devices has changed
            utils.debug("output event detected addition/removal of outputs")
            utils.debug(f"previous profile {mgr.current_profile!r} ==> None")

            req_id = uuid.uuid4()
            utils.trace("apply auto-select profile")
            apply_profile(req_id, mgr.ipc, mgr.config, target_profile_name=None)
            utils.trace(f"--{req_id} completed--")


def apply_profile_fallback() -> None:
    req_id = uuid.uuid4()
    with _apply_lock:
        utils.trace("apply fallback profile")
        apply_profile(req_id, mgr.ipc, Config(), target_profile_name=FALLBACK)
        utils.trace(f"--{req_id} completed--")


def apply_profile_auto_select() -> None:
    req_id = uuid.uuid4()
    with _apply_lock:
        utils.trace(
            f"apply auto-select profile. current profile is {mgr.current_profile}"
        )
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
    utils.trace(f"-------------------{uuid} start --------------------------")
    outputs: List[OutputReply] = mgr.ipc.get_outputs()

    if target_profile_name is FALLBACK:
        utils.debug(f"{target_profile_name!r} is the fallback profile")
        config = Config()
    else:
        # check if current_profile still exists in config
        if target_profile_name and not mgr.is_profile_valid(
            target_profile_name
        ):
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
            commands = f"output {apply.name} enable"

            if m:
                commands += (
                    f" mode {m.width}x{m.height}@{m.refresh}Hz scale {m.scale}"
                )

            if p:
                commands += f" position {p.x} {p.y} "

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


def on_config_reload_event(_ipc: Connection, _event: IpcBaseEvent) -> None:
    utils.trace("handling Sway configuration reload event")
    apply_profile_auto_select()


def start_watcher(config_file_path: Optional[Path]) -> None:
    mgr.load_config(config_file_path)
    mgr.ipc.on(Event.BARCONFIG_UPDATE, on_config_reload_event)
    mgr.ipc.on(Event.OUTPUT, on_output_event)
    mgr.update_output_state(mgr.ipc.get_outputs())

    apply_profile_auto_select()

    if config_file_path:
        utils.debug(
            f"Starting Sway output watcher using {str(config_file_path)!r}"
        )
    else:
        utils.debug(
            "Starting Sway output watcher using fallback configurations"
        )

    mgr.ipc.main()
