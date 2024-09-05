# pylint: disable=redefined-outer-name, line-too-long, too-many-locals

"""Script to profile lambda performance"""

import json
import re
import time
import statistics
import csv
import argparse
from collections import defaultdict
import boto3

request_collection = {}
memory_collection = defaultdict(list)
billed_collection = defaultdict(list)


def execute_query_with_pagination(query, start_time, end_time, client, log_group):
    """Function to execute query with pagination"""

    log_group_name = f'/aws/lambda/{log_group}'

    response = client.start_query(
        logGroupName=log_group_name,
        startTime=start_time,
        endTime=end_time,
        queryString=query,
        limit=10000
    )

    query_id = response['queryId']

    while True:
        query_status = client.get_query_results(queryId=query_id)
        status = query_status['status']
        if status == 'Complete':
            break
        if status in ['Failed', 'Cancelled']:
            print("Query execution failed or was cancelled.")
            break
        time.sleep(1)

    # Retrieve initial results
    results = client.get_query_results(queryId=query_id)
    data = results['results']
    return data


def execute_query_for_minute(query, minute_start_time, minute_end_time, client, log_group):
    """Function to execute query for a given minute"""

    results = execute_query_with_pagination(query, minute_start_time, minute_end_time, client, log_group)
    return results


def execute_query_for_time_range(query, start_time, end_time, client, log_group):
    """Function to execute query for a given time range, minute by minute"""

    all_results = []
    current_time = start_time

    while current_time < end_time:
        minute_start_time = current_time
        minute_end_time = current_time + (300 * 1000)
        results = execute_query_for_minute(query, minute_start_time, minute_end_time, client, log_group)
        all_results.extend(results)
        current_time = minute_end_time

    return all_results


def process_items(items):
    """Function to process a collection for stats"""
    filtered_items = [x for x in items if x is not None]
    if not filtered_items:
        filtered_items = [0]

    minimum = min(filtered_items)
    maximum = max(filtered_items)
    sampled = len(filtered_items)
    average = round(sum(filtered_items) / sampled, 1)
    median = statistics.median(filtered_items)

    return minimum, maximum, average, median, sampled


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Analyze AWS Lambda logs.")
    parser.add_argument('--aws_lambda_log', type=str, help="Lambda log to profile", required=True)
    parser.add_argument('--aws_profile', type=str, help="AWS profile to use", required=True)
    parser.add_argument('--start_time', type=int, help="Start time (hours ago) to analyze", default=1)
    return parser.parse_args()


def setup_aws_client(profile_name):
    """Set up AWS boto3 client for CloudWatch Logs."""
    session = boto3.Session(profile_name=profile_name)
    return session.client('logs')


def compile_patterns():
    """Compile and return regex patterns."""
    request_id_pattern = re.compile(r"RequestId: (\S+)")
    memory_used_pattern = re.compile(r"Max Memory Used: (\d+) MB")
    billed_duration_pattern = re.compile(r"Billed Duration: (\d+) ms")
    return request_id_pattern, memory_used_pattern, billed_duration_pattern


def execute_combined_query(client, log_group_name, start_time, end_time):
    """Execute a combined query on CloudWatch Logs."""
    combined_query = """
    fields @timestamp, @message
    | filter (@message like /Max Memory Used:/ or @message like /aws_request_id/)
    """
    return execute_query_for_time_range(combined_query, start_time, end_time, client, log_group_name)


def process_results(response_query, request_id_pattern, memory_used_pattern, billed_duration_pattern):
    """Process results from the CloudWatch Logs query."""
    request_collection = {}

    for result in response_query:
        text = result[1]['value']

        if 'aws_request_id' in text:
            process_aws_request_id(text, request_collection)
        elif 'Max Memory Used:' in text:
            process_max_memory_used(text, request_id_pattern, memory_used_pattern, billed_duration_pattern, request_collection)

    return request_collection


def process_aws_request_id(text, request_collection):
    """Process and update request collection for aws_request_id."""
    try:
        message = json.loads(json.loads(text).get('message', '{}'))
        request_id = message.get('aws_request_id')
        collection = message.get('collection')

        if request_id:
            request_collection.setdefault(request_id, {}).update({
                "request_id": request_id,
                "collection": collection
            })
    except (json.JSONDecodeError, TypeError):
        pass


def process_max_memory_used(text, request_id_pattern, memory_used_pattern, billed_duration_pattern, request_collection):
    """Process and update request collection for Max Memory Used."""
    request_id_match = request_id_pattern.search(text)
    memory_used_match = memory_used_pattern.search(text)
    billed_duration_match = billed_duration_pattern.search(text)

    if request_id_match and memory_used_match and billed_duration_match:
        request_id = request_id_match.group(1)
        memory_used = int(memory_used_match.group(1))
        billed_duration = int(billed_duration_match.group(1))

        request_collection.setdefault(request_id, {}).update({
            "memory_used": memory_used,
            "billed_duration": billed_duration
        })


def update_memory_billed_collections(request_collection):
    """Update memory and billed collections from request_collection."""
    memory_collection = defaultdict(list)
    billed_collection = defaultdict(list)

    for item in request_collection.values():
        collection = item.get('collection')
        if collection:
            memory_collection[collection].append(item.get('memory_used'))
            billed_collection[collection].append(item.get('billed_duration'))

    return memory_collection, billed_collection


def write_csv(memory_collection, billed_collection):
    """Write collection statistics to a CSV file."""
    csv_filename = "collection_statistics.csv"
    header = [
        "Collection", "Mem Max", "Mem Min", "Mem Med", "Mem Avg",
        "Bill Max", "Bill Min", "Bill Med", "Bill Avg", "Sampled"
    ]

    with open(csv_filename, mode='w', newline='') as file:  # pylint: disable=unspecified-encoding
        writer = csv.writer(file)
        writer.writerow(header)

        for key in sorted(memory_collection.keys()):
            item = memory_collection.get(key, [])
            bill_item = billed_collection.get(key, [])

            minimum, maximum, average, median, sampled = process_items(item)
            bill_min, bill_max, bill_avg, bill_med, _ = process_items(bill_item)

            row = [
                key, maximum, minimum, median, average,
                bill_max, bill_min, bill_med, bill_avg, sampled
            ]
            writer.writerow(row)


def main():
    """Main function for the script."""
    args = parse_arguments()
    client = setup_aws_client(args.aws_profile)

    request_id_pattern, memory_used_pattern, billed_duration_pattern = compile_patterns()

    start_time = int((time.time() - args.start_time * 3600) * 1000)
    end_time = int((time.time()) * 1000)

    response_query = execute_combined_query(client, args.aws_lambda_log, start_time, end_time)

    request_collection = process_results(
        response_query, request_id_pattern, memory_used_pattern, billed_duration_pattern
    )

    memory_collection, billed_collection = update_memory_billed_collections(request_collection)

    write_csv(memory_collection, billed_collection)


if __name__ == "__main__":
    main()
