# pylint: disable=line-too-long, too-many-locals

"""
==============
regression.py
==============

Test TIG on all our collections.
"""
import argparse
import os
import subprocess
import json
from collections import defaultdict
from pathlib import Path
import requests


def make_cli_call(command):
    """Function to make cli calls"""
    try:
        output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
        return output.decode("utf-8")  # Decoding the output bytes to string
    except subprocess.CalledProcessError as e:
        return e.output.decode("utf-8")  # Decoding the error output bytes to string


def download_configs(config_dir):
    """Function to download all the forge tig configs from github"""
    os.makedirs(config_dir, exist_ok=True)

    print("..... downloading configuration files")
    api_url = "https://api.github.com/repos/podaac/forge-tig-configuration/contents/config-files"
    response = requests.get(api_url, timeout=60)

    if response.status_code == 200:
        for file in response.json():
            url = file.get('download_url')
            config_file = requests.get(url, timeout=60)
            local_filename = file.get('name')
            local_path = os.path.join(config_dir, local_filename)
            with open(local_path, 'wb') as file:
                file.write(config_file.content)


def main():
    """Main function for regression"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--backfill_config', type=str, required=True, help="Path to backfill config")
    parser.add_argument('--type', type=str, choices=['forge', 'tig', 'forge-py'], help="Regression type")

    args = parser.parse_args()

    config_directory = Path(__file__).resolve().parent / "dl_configs"
    download_configs(config_directory)
    files = list(config_directory.glob("*.cfg"))  # Only process .cfg files

    file_categories = defaultdict(list)

    for file_path in files:
        with file_path.open("r") as open_file:
            data = json.load(open_file)

        if data.get("footprint"):
            key = "forge_py" if data.get("footprinter") == "forge-py" else "forge"
            file_categories[key].append(file_path.name)

        if data.get("imgVariables"):
            file_categories["tig"].append(file_path.name)

    # Extract and sort lists
    forge_py_file = sorted(file_categories["forge_py"])
    forge_file = sorted(file_categories["forge"])
    tig_file = sorted(file_categories["tig"])

    # Define regression type mapping
    regression_args = {
        "forge": ("--image off --footprint force --dmrpp off", forge_file),
        "tig": ("--image force --footprint off --dmrpp off", tig_file),
        "forge-py": ("--image off --footprint force --dmrpp off", forge_py_file),
    }

    additional_arguments, regression_files_list = regression_args.get(args.type, (None, [f.name for f in files]))

    for file_name in regression_files_list:
        collection = Path(file_name).stem  # Removes the .cfg extension
        cli_command = f'backfill --config {args.backfill_config} --collection {collection} '
        if additional_arguments:
            cli_command += additional_arguments
        result = make_cli_call(cli_command)
        print(result)


if __name__ == "__main__":
    main()
