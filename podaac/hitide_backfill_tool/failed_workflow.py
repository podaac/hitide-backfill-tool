"""Script to get unique errors from step function workflows"""
# pylint: disable=C0103, C0301

import argparse
import json
import boto3
from fuzzywuzzy import fuzz


def parse_args():
    """function to get argument parameters"""

    parser = argparse.ArgumentParser(description='Process some integers.')

    parser.add_argument('--workflow_arn', help='aws workflow arn', required=True)
    parser.add_argument('--profile_name', help='aws profile name', required=True)
    parser.add_argument('--limit', help='aws profile name', type=int, required=False)

    return parser.parse_args()


if __name__ == "__main__":

    args = parse_args()
    workflow_arn = args.workflow_arn
    profile_name = args.profile_name
    limit = args.limit
    processed = 0

    session = boto3.Session(profile_name=profile_name)
    client = session.client('stepfunctions')

    errors = []

    max_results = 1000
    if limit and limit <= 1000:
        max_results = limit
    elif limit and limit > 1000:
        max_results = 1000

    response = client.list_executions(
        stateMachineArn=workflow_arn,
        statusFilter='FAILED',
        maxResults=max_results,
    )

    next_token = response.get('nextToken')

    while next_token is not None:

        next_token = response.get('nextToken')

        for a in response.get('executions'):
            execution_arn = a.get('executionArn')

            response_execution = client.get_execution_history(
                executionArn=execution_arn
            )

            res = response_execution.get('events')[-2]
            execution_input = res.get('stateEnteredEventDetails')['input']
            execution_input_dict = json.loads(execution_input)
            details = execution_input_dict.get('details')
            exception = execution_input_dict.get('exception')
            execution_name = execution_input_dict['cumulus_meta']['execution_name']

            granule_id = execution_input_dict.get('payload').get('granules')[0].get('granuleId')
            collection = execution_input_dict.get('payload').get('granules')[0].get('dataType')

            if details:
                error_string = details.get('errorMessage')
                if len(errors) == 0:
                    errors.append({'error': error_string, 'execution_name': execution_name, 'execution_arn': execution_arn, 'granule_id': granule_id, 'collection': collection})
                else:
                    max_ratio = 0
                    for e in errors:
                        ratio = fuzz.partial_ratio(e, error_string)
                        max_ratio = max(ratio, max_ratio)

                    if max_ratio < 50:
                        errors.append({'error': error_string, 'execution_name': execution_name, 'execution_arn': execution_arn, 'granule_id': granule_id, 'collection': collection})
            elif exception:
                error_string = exception.get('Cause')
                if len(errors) == 0:
                    errors.append({'error': error_string, 'execution_name': execution_name, 'execution_arn': execution_arn, 'granule_id': granule_id, 'collection': collection})
                else:
                    max_ratio = 0
                    for e in errors:
                        ratio = fuzz.partial_ratio(e, error_string)
                        max_ratio = max(ratio, max_ratio)

                    if max_ratio < 50:
                        errors.append({'error': error_string, 'execution_name': execution_name, 'execution_arn': execution_arn, 'granule_id': granule_id, 'collection': collection})
            else:
                print("Unprocessed ERROR MESSAGE")
                print(json.loads(execution_input))

        processed += max_results

        if next_token:

            if limit and processed < limit:

                if limit - processed < 1000:
                    max_results = limit - processed
                else:
                    max_results = 1000

            elif processed == limit:
                break

            response = client.list_executions(
                stateMachineArn=workflow_arn,
                statusFilter='FAILED',
                maxResults=max_results,
                nextToken=next_token
            )

        else:
            next_token = None

    print("Number of unique errors found:", len(errors))
    for e in errors:
        print('Execution UUID : ', e.get('execution_name'))
        print('Execution Arn : ', e.get('execution_arn'))
        print('Collection :', e.get('collection'))
        print('Granule Id :', e.get('granule_id'))
        print('Error : ', e.get('error'))
        print("#############################################################")
