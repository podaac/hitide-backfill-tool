import sys
import json
import re

def read_json_file(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in file '{file_path}'.")
    return {}

if __name__ == '__main__':
    if len(sys.argv) < 5:
        print("Usage: python script.py <env> <commit_url> <branch_url> <app_version>")
        sys.exit(1)

    env = sys.argv[1]
    commit_url = sys.argv[2]
    branch_url = sys.argv[3]
    app_version = sys.argv[4]

    # Load environment-specific data
    file_path = f'terraform_env/{env}.json'
    json_data = read_json_file(file_path)

    # === 1. override.tf.json ===
    override_data = {
        'module': {
            'tig': {
                'source': json_data.get('tig_source'),
                'lambda_container_image_uri': json_data.get('tig_image')
            },
            'forge_module': {
                'source': json_data.get('forge_source'),
                'lambda_container_image_uri': json_data.get('forge_image')
            },
            'forge_py_module': {
                'source': json_data.get('forge_py_source'),
                'lambda_container_image_uri': json_data.get('forge_py_image')
            },
            'backfill_lambdas': {
                'source': json_data.get('backfill_lambdas_source')
            },
            'postworkflow_normalizer_module': {
                'source': json_data.get('postworkflow_normalizer_source')
            }
        }
    }

    with open('override.tf.json', 'w') as f:
        json.dump(override_data, f, indent=2)

    metadata_inputs = dict(json_data)  # copy all original values
    metadata_inputs["commit_url"] = commit_url
    metadata_inputs["branch_url"] = branch_url
    metadata_inputs["app_version"] = str(app_version)

    with open("dmrpp.tf", "r") as file:
        file_content = file.read()

    # Regular expression to extract docker image version
    pattern = r'docker_image\s*=\s*"\$\{[^}]+\}:v([\d\.]+)"'
    match = re.search(pattern, file_content)

    if match:
        docker_version = match.group(1)
        metadata_inputs["dmrpp_version"] = str(docker_version)

    with open('backfill_tool_metadata.json', 'w') as f:
        json.dump(metadata_inputs, f, indent=2)
