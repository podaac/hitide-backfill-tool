import json
import requests
import pytest
import pathlib

# Load JSON file
def load_json(filepath):
    with open(filepath, "r") as f:
        return json.load(f)

# Extract only the URLs that are meant for downloading
def extract_download_urls(data):
    return [url for key, url in data.items() if url.startswith("https://github.com") and url.endswith(".zip")]

# Get all JSON files relative to this script's location
SCRIPT_DIR = pathlib.Path(__file__).parent.resolve()
JSON_FOLDER = SCRIPT_DIR / "../terraform-deploy/terraform_env"
json_files = list(JSON_FOLDER.glob("*.json"))

@pytest.mark.parametrize("file", json_files, ids=[f.name for f in json_files])
def test_urls_in_file(file):
    data = load_json(file)
    urls = extract_download_urls(data)
    
    if not urls:
        pytest.skip(f"No URLs to test in {file}")
    
    for url in urls:
        response = requests.head(url, allow_redirects=True, timeout=5)
        assert response.status_code == 200, f"URL {url} in {file} is not reachable, status code: {response.status_code}"
