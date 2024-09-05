"""Parse cli args"""

import sys
from argparse import ArgumentParser, Namespace
from podaac.hitide_backfill_tool.file_util import load_yaml_file


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
    "footprint": "on",
    "image": "on",
    "dmrpp": "off",
    "dmrpp_min_version": "3.21.0-272",     # Important: Update this version when updating the
                                           #            backend dmrpp_generator
    "preview": False,
    "use_data_url": False,
    "page_size": 2000,
    "geometries": ["GPolygons", "Lines"],
    "log_level": "INFO"
}


def create_parser():
    """Create a argparse parser for the backfill cli"""

    parser = ArgumentParser()
    parser.add_argument("--config")

    parser.add_argument("--cmr", choices=["ops", "uat", "sit"])
    parser.add_argument("-c", "--collection")
    parser.add_argument("--provider")
    parser.add_argument("-sd", "--start-date")
    parser.add_argument("-ed", "--end-date")
    parser.add_argument("--page-size", type=int)
    parser.add_argument("--page-limit", type=int)
    parser.add_argument("--edl-token")
    parser.add_argument("--launchpad-token")
    parser.add_argument("--cmr-search-after")

    parser.add_argument("-g", "--geometry", dest="geometries",
                        action="append", default=None)
    parser.add_argument("--footprint", choices=["on", "off", "force"])
    parser.add_argument("--image", choices=["on", "off", "force"])
    parser.add_argument("--dmrpp", choices=["on", "off", "force"])
    parser.add_argument("--dmrpp-min-version")
    parser.add_argument("--use-data-url", action="store_true", default=None)

    parser.add_argument("--cumulus", choices=["ops", "uat", "sit",
                                              "swot-sit", "swot-uat", "swot-ops"])
    parser.add_argument("--cumulus-configurations")

    parser.add_argument("--preview", action="store_true", default=None)
    parser.add_argument("--sns-arn")
    parser.add_argument("--aws-profile")
    parser.add_argument("--message_file")
    parser.add_argument("--message-limit", type=int)
    parser.add_argument("--user")

    parser.add_argument("--log-file")
    parser.add_argument("--log-level")

    parser.add_argument('--cycles', type=str, help='List of cycles or a single cycle', default=None)
    parser.add_argument('--sort-order', type=str, help="cmr search start date sorting order",
                        choices=["descending", "ascending"])

    parser.add_argument("--default_message_config", type=str,
                        help="defaut message config to construct messages", default=None)

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

    if merged_config.default_message_config is None:
        raise Exception("please specify path to default message config")

    return merged_config
