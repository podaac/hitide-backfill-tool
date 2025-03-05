import json
import pytest
import re
from urllib.parse import urlparse, unquote
from pathlib import Path

def extract_version_from_url(url):
    """Extract both folder version and file version from a source URL"""
    decoded_url = unquote(url)
    parsed_url = urlparse(decoded_url)
    path_parts = parsed_url.path.split('/')
    
    # Get folder version (after /download/)
    try:
        download_index = path_parts.index('download')
        folder_version = path_parts[download_index + 1]
    except (ValueError, IndexError):
        return None, None
    
    # Get file version (from zip filename)
    filename = path_parts[-1]
    # Updated pattern to handle various version formats
    file_version_match = re.search(r'[\w-]+?-(\d+\.\d+\.\d+(?:[-+]?\w+(?:\.\d+)?)?).zip$', filename)
    file_version = file_version_match.group(1) if file_version_match else None
    
    return folder_version, file_version

def normalize_for_docker(version):
    """Convert + to - for Docker compatibility"""
    return version.replace('+', '-') if version else version

# Get all JSON files from the terraform_env directory
SCRIPT_DIR = Path(__file__).parent.resolve()
JSON_FOLDER = SCRIPT_DIR / "../terraform-deploy/terraform_env"
json_files = list(JSON_FOLDER.glob("*.json"))

@pytest.mark.parametrize("json_file", json_files, ids=[f.name for f in json_files])
def test_version_consistency(json_file):
    # Load JSON file
    with open(json_file) as f:
        data = json.load(f)
    
    # Process each source URL
    for key, url in data.items():
        if not key.endswith('_source'):
            continue
            
        # Extract versions from source URL
        folder_version, file_version = extract_version_from_url(url)
        
        # Test 1: Folder version must match file version
        assert folder_version == file_version, \
            f"In file {json_file.name}, version mismatch in {key}:\n" \
            f"Folder version: {folder_version}\n" \
            f"File version: {file_version}"
            
        # Test 2: If there's a corresponding image, versions must match (accounting for + to -)
        image_key = key.replace('_source', '_image')
        if image_key in data:
            # Extract version from Docker image tag
            image_version = data[image_key].split(':')[-1]
            normalized_folder_version = normalize_for_docker(folder_version)
            
            assert image_version == normalized_folder_version, \
                f"In file {json_file.name}, version mismatch between source and image for {key}:\n" \
                f"Source version (normalized): {normalized_folder_version}\n" \
                f"Image version: {image_version}"