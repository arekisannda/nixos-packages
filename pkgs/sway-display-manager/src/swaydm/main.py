#!/usr/bin/env python3

from argparse import ArgumentParser

from . import command, config, ipc, manager, utils


def main():
    arguments_parser = ArgumentParser()
    command_parser = arguments_parser.add_subparsers(dest="command")

    # global options
    arguments_parser.add_argument(
        '-l',
        '--log-level',
        type=str,
        default='INFO',
        choices=['TRACE', 'DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Set logging level. (default: %(default)s)',
    )

    arguments_parser.add_argument(
        '-s',
        '--socket',
        type=str,
        default=ipc.DEFAULT_SOCKET_PATH,
        help='Use the specified socket. (default: %(default)s)',
    )

    arguments_parser.add_argument(
        '-c', '--config', type=str, help='Specifies a config file.'
    )

    switch_parser = command_parser.add_parser(
        "switch", help="Switch to profile"
    )
    switch_parser.add_argument("profile", type=str, help="Profile name")

    status_parser = command_parser.add_parser(
        "status", help="Show display manager status"
    )
    status_parser.add_argument(
        "-V", "--verbose", action='store_true', help='Enable verbose output.'
    )

    status_parser.add_argument(
        "--json", action='store_true', help='Output in JSON format.'
    )

    command_parser.add_parser("list", help="List available profiles")
    command_parser.add_parser("reload", help="Reload configuration file")
    command_parser.add_parser(
        "toggle", help="Toggle display manager auto apply"
    )

    arguments = arguments_parser.parse_args()
    utils.setup(arguments.log_level)
    ipc.setup(arguments.socket)

    match arguments.command:
        case "switch":
            ipc.switch_profile(arguments.profile)
        case "reload":
            ipc.reload_config()
        case "toggle":
            ipc.toggle_auto_apply()
        case "list":
            ipc.list_profiles()
        case "status":
            ipc.status(verbose=arguments.verbose, json=arguments.json)
        case _:
            config_path = config.find_config_file(arguments.config)
            ipc.start_server(command.command_handler)
            manager.start_watcher(config_path)
