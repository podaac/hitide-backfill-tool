"""
==============
regression.py
==============

Test TIG on all our collections.
"""
import argparse
import os
import subprocess
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
    """main function for regression"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--backfill_config', type=str,
                        help="path to backfill config", required=True)
    args = parser.parse_args()

    test_dir = os.path.dirname(os.path.realpath(__file__))
    config_directory = f'{test_dir}/dl_configs'
    download_configs(config_directory)

    files = os.listdir(config_directory)
    print(files)

    for _file in files:
        collection = _file.strip('.cfg')
        cli_command = f'backfill --config {args.backfill_config} --collection {collection}'
        result = make_cli_call(cli_command)
        print(result)


if __name__ == "__main__":
    main()
