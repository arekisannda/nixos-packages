from functools import partial

from i3ipc import Connection, Event

from . import layout as sway_layout
from .schema import Config
from . import utils


def on_output_event(config: dict, ipc: Connection, event: Event) -> None:
    apply_layout(config, ipc)


def apply_layout(config: Config, ipc: Connection) -> None:
    outputs = ipc.get_outputs()
    result = sway_layout.get_layout(config, outputs)
    if not result:
        return

    layout_name, layout, commands = result

    output_by_name = {o.name: o for o in outputs}

    for apply in layout:
        current = output_by_name.get(apply.name)
        if current and sway_layout.is_output_already_configured(current, apply):
            utils.debug(f"{layout_name} is already the desired state, skip")
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


    utils.info(f"Current layout: {layout_name}")
    utils.debug(f"Layout: {layout}")

    alias_to_output_name = {apply.alias: apply.name for apply in layout if apply.alias}
    utils.debug(f"Aliases to output: {alias_to_output_name}")

    if commands:
        utils.debug("Run commands")
        for ind, cmd in enumerate(commands):
            cmd = cmd.format_map(alias_to_output_name)
            utils.debug(f"{ind}: {cmd}")
            ipc.command(cmd)


def start_watcher(config: Config) -> None:
    ipc = Connection()
    ipc.on(Event.OUTPUT, partial(on_output_event, config))

    apply_layout(config, ipc)

    ipc.main()
