#!/usr/bin/env python3

from argparse import ArgumentParser

from . import config, sway, utils


def main():
    arguments_parser = ArgumentParser()

    arguments_parser.add_argument('-c',
                     '--config',
                     type=str,
                     help='Specifies a config file')
    arguments_parser.add_argument('-l',
                     '--log-level',
                     type=str,
                     default='INFO',
                     choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                     help='Set logging level.')

    arguments = arguments_parser.parse_args()

    utils.setup(arguments.log_level)

    config_path = config.find_config_file(arguments.config)

    sway.start_watcher(config_path)
