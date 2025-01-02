import sys
import json

def read_json_file(file_path):
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
            return data
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
    except json.JSONDecodeError:
        print(f"Error: Unable to decode JSON from file '{file_path}'. Check if the file contains valid JSON.")

if __name__ == '__main__':

    env = sys.argv[1]

    # Replace 'your_file.json' with the actual path to your JSON file
    file_path = f'terraform_env/{env}.json'
    
    # Read JSON file
    json_data = read_json_file(file_path)

    data = {
        'module': {
            'tig': {'source': json_data.get('tig_source'), 'lambda_container_image_uri': json_data.get('tig_image')},
            'forge_module': {'source': json_data.get('forge_source'), 'lambda_container_image_uri': json_data.get('forge_image')},
            'forge_py_module': {'source': json_data.get('forge_py_source'), 'lambda_container_image_uri': json_data.get('forge_py_image')},
            'backfill_lambdas': {'source': json_data.get('backfill_lambdas_source')},
            'postworkflow_normalizer_module': {'source': json_data.get('postworkflow_normalizer_source')},
        }
    }

    with open('override.tf.json', 'w') as f:
        json.dump(data, f)