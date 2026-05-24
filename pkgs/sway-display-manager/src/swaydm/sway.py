import threading
import uuid
from pathlib import Path
from typing import List, Optional

from i3ipc import Connection, Event, OutputEvent, OutputReply

from . import config, profile, utils
from .datatypes import FALLBACK, ApplyProfile, DisplayManager, StatusOutput

mgr: DisplayManager = DisplayManager(config_loader=config.load_config)

_apply_lock = threading.Lock()


def on_output_event(ipc: Connection, event: OutputEvent) -> None:
    utils.trace(f"handling {event.ipc_data}")
    appply_profile_auto_select()


def appply_profile_auto_select() -> None:
    req_id = uuid.uuid4()
    with _apply_lock:
        utils.trace("apply auto-select profile")
        apply_profile(req_id, mgr.ipc, target_profile_name=mgr.current_profile)
        utils.trace(f"--{req_id} completed--")


def appply_profile_target(target_profile_name: str) -> None:
    req_id = uuid.uuid4()
    with _apply_lock:
        utils.trace(f"apply {target_profile_name}")
        apply_profile(req_id, mgr.ipc, target_profile_name=target_profile_name)
        utils.trace(f"--{req_id} completed--")


def apply_profile(
    uuid: uuid.UUID, ipc: Connection, target_profile_name: Optional[str]
) -> None:
    if not mgr.is_active():
        utils.debug("Display manager auto-apply is paused")
        return

    utils.trace(f"-------------------{uuid} start --------------------------")
    outputs: List[OutputReply] = ipc.get_outputs()

    # check if current_profile still exists in config
    if mgr.get_profile(target_profile_name) is None:
        utils.debug(
            f"{target_profile_name!r} is not in the list of available profiles. switching to auto-selected profile"
        )
        target_profile_name = None

    target_profile: ApplyProfile = profile.get_profile(
        mgr.config, outputs, target_profile_name
    )

    if target_profile_name and target_profile.name == FALLBACK:
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

    mgr.current_profile = target_profile.name
    utils.trace(f"-------------------{uuid} end --------------------------")


def command_handler(command: str) -> str:
    parts = command.split()
    if not parts:
        return "error: empty command"

    match parts[0]:
        case "toggle_auto_apply":
            utils.info("Toggle display manager auto")
            mgr.toggle_auto_apply()
            appply_profile_auto_select()
            if mgr.is_active():
                return "Auto-apply resumed"
            else:
                return "Auto-apply paused"

        case "reload":
            utils.info("Reloading configurations")
            mgr.reload_config()
            appply_profile_auto_select()
            return "Configuration reloaded"

        case "list_profiles":
            return f"{'\n'.join([p.name for p in mgr.config.profiles])}"

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
                    return output_info.format(verbose)
                case "status_json":
                    return output_info.format_json(verbose)

        case "switch_profile":
            if len(parts) < 2:
                return "error: usage: switch <profile>"

            profile_name = parts[1]
            utils.info(f"Switching profile to {profile_name}")
            if mgr.get_profile(profile_name) is None:
                utils.warning(f"{profile_name!r} is not a valid profile.")
                return f"error: {profile_name!r} is not a valid profile."
            try:
                appply_profile_target(profile_name)
            except RuntimeError as e:
                utils.warning(f"Failed to apply profile: {e}")
                return f"Unable to switch to {profile_name!r}"
            return f"Switched to {profile_name!r}"

        case _:
            return f"error: unknown command {parts[0]!r}"


def start_watcher(config_file_path: Path) -> None:
    mgr.load_config(config_file_path)
    mgr.ipc.on(Event.OUTPUT, on_output_event)

    appply_profile_target(target_profile_name=None)

    utils.debug(f"Starting Sway output watcher {str(config_file_path)!r}")
    mgr.ipc.main()
