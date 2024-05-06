"""Script to run forge as a cli command"""
# pylint: disable=R0801, E1101

import logging
import sys
import copy
import json
from datetime import datetime, timezone
import xarray as xr

from podaac.forge_py.args import parse_args
from podaac.forge_py.file_util import make_absolute
from podaac.forge_py import forge


def logger_from_args(args):
    """Return configured logger from parsed cli args."""

    if args.log_file:
        logging.basicConfig(filename=make_absolute(args.log_file))
    logger = logging.getLogger("backfill")
    logger.setLevel(getattr(logging, args.log_level))
    logger.addHandler(logging.StreamHandler(sys.stdout))
    return logger


def object_to_str(obj):
    """Return formatted string, given a python object."""

    vars_dict = vars(obj)
    vars_string = ""
    for key in vars_dict.keys():
        vars_string += f"  {key} -> {vars_dict[key]}\n"
    return vars_string


def safe_log_args(logger, args):
    """Log the parsed cli args object without showing tokens."""

    args_copy = copy.copy(args)
    logger.debug(f"\nCLI args:\n{object_to_str(args_copy)}\n")


def main(args=None):
    """Main script for backfilling from the cli"""

    # load args
    args = parse_args(args)

    logger = logger_from_args(args)

    logger.info(f"Started forge-py: "                                 # pylint: disable=W1203
                f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S %Z')}")

    safe_log_args(logger, args)

    config_file = args.config
    local_file = args.granule

    with open(config_file) as config_f:
        read_config = json.load(config_f)

    longitude_var = read_config.get('lonVar')
    latitude_var = read_config.get('latVar')
    is360 = read_config.get('is360', False)

    thinning_fac = read_config.get('footprint', {}).get('thinning_fac', 100)
    alpha = read_config.get('footprint', {}).get('alpha', 0.05)
    strategy = read_config.get('footprint', {}).get('strategy', None)
    simplify = read_config.get('footprint', {}).get('simplify', 0.1)

    # Generate footprint
    with xr.open_dataset(local_file, decode_times=False) as ds:
        lon_data = ds[longitude_var]
        lat_data = ds[latitude_var]
        wkt_representation = forge.generate_footprint(lon_data, lat_data, thinning_fac=thinning_fac, alpha=alpha, is360=is360, simplify=simplify, strategy=strategy)

    if args.output_file:
        with open(args.output_file, "w") as json_file:
            json.dump(wkt_representation, json_file)

    print(wkt_representation)

    logger.info(f"Finished forge-py: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S %Z')}")  # pylint: disable=W1203


if __name__ == "__main__":
    main()
