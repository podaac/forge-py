"""Parse cli args"""

import sys
from argparse import ArgumentParser, Namespace
from podaac.forge_py.file_util import load_yaml_file


def merge_dicts(defaults, config, cli):
    """Return dict that is merge of default config values, config file values and cli args"""
    keys = {**cli, **config, **defaults}.keys()
    output = {}
    for key in keys:
        output[key] = ((cli.get(key) is not None and cli.get(key)) or
                       (config.get(key) is not None and config.get(key)) or
                       defaults.get(key))
    return output


default_config = {
    "log_level": "INFO"
}


def create_parser():
    """Create a argparse parser for the backfill cli"""

    parser = ArgumentParser()
    parser.add_argument("-c", "--config", required=True)
    parser.add_argument("-g", "--granule", required=True)
    parser.add_argument("-o", "--output_file")
    parser.add_argument("--log-file")
    parser.add_argument("--log-level")

    return parser


def parse_args(args=None):
    """Return argparse namespace with merged config values (defaults + config_file + cli_args)

    Args calculated from input string, string array, or if neither is provided, from sys.argv"""

    if args is None:
        args = sys.argv[1:]
    elif isinstance(args, str):
        args = args.split()

    parser = create_parser()
    args = parser.parse_args(args)
    config = {}
    if args.config:
        config = load_yaml_file(args.config)

    args = vars(args)
    merged_dict = merge_dicts(default_config, config, args)
    merged_config = Namespace(**merged_dict)
    return merged_config
