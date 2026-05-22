#!/usr/bin/env python3

import os
from argparse import ArgumentParser
from pathlib import Path

from . import config, sway, utils


def main():
    arguments_parser = ArgumentParser()

    grp = arguments_parser.add_mutually_exclusive_group()
    grp.add_argument('-c',
                     '--config',
                     default='$XDG_CONFIG_HOME/sway/display.yaml',
                     type=str,
                     help='Specifies a config file. (default: %(default)s)')
    grp.add_argument('-l',
                     '--log-level',
                     type=str,
                     default='INFO',
                     choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                     help='Set logging level.')

    arguments = arguments_parser.parse_args()
    if not arguments.config:
        arguments_parser.error("--config is required")

    utils.setup(arguments.log_level)

    config_path = Path(os.path.expandvars(os.path.expanduser(arguments.config)))

    if not config_path.is_file():
        arguments_parser.error(f"config file not found: {config_path}")

    config_file = config.load_config(config_path)
    utils.debug(f"Loaded {config_path}")

    sway.start_watcher(config_file)
