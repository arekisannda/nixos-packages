from pathlib import Path
from typing import List

from i3ipc import Connection, Event, OutputReply

from . import config as dm_config
from . import layout as dm_layout
from . import utils
from .schema import Config, ApplyLayout 


_CURRENT_CONFIGS = Config()
_LAST_TARGET = None

def on_output_event(ipc: Connection, event: Event) -> None:
    apply_layout(_CURRENT_CONFIGS, ipc)


def apply_layout(config: Config, ipc: Connection) -> None:
    outputs: List[OutputReply] = ipc.get_outputs()
    layout: ApplyLayout = dm_layout.get_layout(config, outputs, _LAST_TARGET)
    if not layout:
        return

    output_by_name = {o.name: o for o in outputs}

    for apply in layout.outputs:
        current = output_by_name.get(apply.name)
        if current and dm_layout.is_output_already_configured(current, apply):
            utils.debug(f"{layout.name} is already the desired state, skip")
            continue

        if apply.active:
            m, p = apply.mode, apply.position
            commands = (
                f"output {apply.name} enable "
                f"mode {m.width}x{m.height}@{m.refresh}Hz scale {m.scale} "
                f"position {p.x} {p.y} "
            )

            utils.debug(f"command => {commands}")
            ipc.command(commands)
        else:
            utils.debug(f"output {apply.name} disable;")
            ipc.command(f"output {apply.name} disable;")


    utils.info(f"Current layout: {layout.name}")
    utils.debug(f"Layout: {layout.outputs}")

    alias_to_output_name = {apply.alias: apply.name for apply in layout.outputs if apply.alias}
    utils.debug(f"Aliases: {alias_to_output_name}")

    if layout.commands:
        utils.debug("Run commands")
        for ind, cmd in enumerate(layout.commands):
            cmd = cmd.format_map(alias_to_output_name)
            utils.debug(f"{ind}: {cmd}")
            ipc.command(cmd)


def start_watcher(config_file_path: Path) -> None:
    config = dm_config.load_config(config_file_path)

    ipc = Connection()
    ipc.on(Event.OUTPUT, on_output_event)

    apply_layout(config, ipc)

    ipc.main()
