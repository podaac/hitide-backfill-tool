"""
==============
regression.py
==============

Test TIG on all our collections.
"""
import requests
import os
import subprocess


def make_cli_call(command):
    try:
        output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
        return output.decode("utf-8")  # Decoding the output bytes to string
    except subprocess.CalledProcessError as e:
        return e.output.decode("utf-8")  # Decoding the error output bytes to string


def download_configs(config_dir):

    os.makedirs(config_dir, exist_ok=True)

    print("..... downloading configuration files")
    api_url = f"https://api.github.com/repos/podaac/forge-tig-configuration/contents/config-files"
    response = requests.get(api_url)

    if response.status_code == 200:
         for file in response.json():
            url = file.get('download_url')
            config_file = requests.get(url)
            local_filename = file.get('name')
            local_path = os.path.join(config_dir, local_filename)
            with open(local_path, 'wb') as file:
                file.write(config_file.content)

if __name__ == "__main__":

    test_dir = os.path.dirname(os.path.realpath(__file__))
    config_dir = f'{test_dir}/dl_configs'
    #download_configs(config_dir)

    files = os.listdir(config_dir)
    print(files)

    for file in files:
        collection = file.strip('.cfg')
        command = f'backfill --config backfill_uat.cfg --collection {collection}'
        result = make_cli_call(command)
        print(result)

