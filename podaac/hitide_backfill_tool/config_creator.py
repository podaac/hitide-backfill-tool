"""
This module is for creating a config file that can be used by the backfill tool
"""

import argparse
from .file_util import make_absolute


CONFIG_TEMPLATE = """
### CMR SEARCH OPTIONS ###
cmr: <<<cmr>>> # required
collection: MODIS_A-JPL-L2P-v2019.0  # required
provider: <<<provider>>>  # required
# start_date: "2020-01-01T00:00:00Z"
# end_date: "2020-02-01T00:00:00Z"
# page_size: 2000
# page_limit: 2
# edl_token: insert-edl-token-here
# launchpad_token: insert-launchpad-token-here

### GRANULE PARSING OPTIONS ###
# geometries: [GPolygons, Lines]
# footprint: "on"
# image: "on"
# dmrpp: "on"
# dmrpp_min_version: "3.20.9-92"
use_data_url: true

### FOR FINDING MESSAGE INFORMATION ###
cumulus: <<<cumulus>>>  # required
cumulus_configurations: insert-cumulus-configurations-directory-location-here  # required

### MESSAGE SENDING OPTIONS ###
# sns_arn: <<<sns_arn>>>
# aws_profile: <<<aws_profile>>>
# message_file: /path/to/message/file.txt
# message_limit: 20
# user: insert-optional-username-here
# preview: true

### LOGS ###
# log_file: /path/to/desired/log/file.txt
# log_level: DEBUG

"""


def create_config_string(cmr, provider, cumulus, aws_profile):
    """Create a yaml formatted config string with params filled in"""
    txt = CONFIG_TEMPLATE
    txt = txt.replace("<<<cmr>>>", cmr)
    txt = txt.replace("<<<provider>>>", provider)
    txt = txt.replace("<<<cumulus>>>", cumulus)
    txt = txt.replace("<<<aws_profile>>>", aws_profile)
    return txt


def format_arg_name(name):
    """Removes leading "--" and converts "-" to "_"

    Ex// --optional-value -> optional_value
    """
    return name.replace("--", "").replace("-", "_")


def parse_args(args):
    """Parse arguments given from command line"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", required=True, choices=["ops", "uat", "sit"])
    parser.add_argument("--filename", required=True)
    return parser.parse_args(args)


def create_defaults(env):
    """Given a general environment name, generate default values for cmr,
       provider, cumulus, sns_arn, and aws_profile
    """
    if env == "ops":
        return {
            "cmr": "ops",
            "provider": "pocloud",
            "cumulus": "ops",
            "aws_profile": "ngap-services-ops"
        }

    if env == "uat":
        return {
            "cmr": "uat",
            "provider": "pocloud",
            "cumulus": "uat",
            "aws_profile": "ngap-services-uat"
        }

    if env == "sit":
        return {
            "cmr": "uat",
            "provider": "pocumulus",
            "cumulus": "sit",
            "aws_profile": "ngap-services-sit"
        }

    raise f"create_defaults({env}) - env must be ops | uat | sit"


def create_config(args=None):
    """Create a config file given command line arguments"""
    args = parse_args(args)
    print(args)

    defaults = create_defaults(args.env)
    config = create_config_string(**defaults)
    filename = make_absolute(args.filename)
    with open(filename, "w", encoding='utf-8') as file:
        file.write(config)
