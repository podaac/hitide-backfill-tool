"""
This module contains methods for retrieving configurations that
are used for creating cumulus messages
"""

import os
from pathlib import Path

from .file_util import load_json_file, make_absolute


def get_message_config(env, config_file=None):
    """Retrieve message config file.

    The message config is specific to an environment (ops, uat, or sit) and
    is the same for all collections in that environment
    """
    if config_file is not None:
        message_config = load_json_file(config_file)
    else:
        message_config = load_json_file(
            "default_message_config.json", relative_to=__file__)
    return message_config.get(env, {})


def get_collection_config(base_dir, collection, env, logger):
    """Retrieve a collection config

    A collection config is specific to a collection in a certain
    environment (e.g. MODIS_A-JPL-L2P-v2019.0 in uat)

    base_dir is the root directory for cumulus-configurations
    repository
    """
    base_dir = make_absolute(base_dir)

    env_dir = ""
    if "sit" in env:
        env_dir = "sit"
    elif "uat" in env:
        env_dir = "uat"
    elif "ops" in env:
        env_dir = "ops"

    pattern = f"**/{env_dir}/**/{collection}.json"
    logger.info(f"collection config: searching {base_dir} for {pattern}")

    if not os.path.isdir(base_dir):
        raise Exception(
            f"Tried to find cumulus-configurations directory: {base_dir}. It is not a directory")

    path = Path(base_dir)
    files = path.glob(pattern)
    try:
        file = next(files)
        logger.info(f"collection config: found {file}")
        return load_json_file(file)
    except Exception as exc:
        raise Exception("Could not find collection config") from exc
