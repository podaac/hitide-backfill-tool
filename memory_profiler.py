import boto3
import json
import re
import time
import statistics
import csv

session = boto3.Session(profile_name="service-uat")
client = session.client('logs')

request_collection = {}
memory_collection = {}
billed_collection = {}


def query_cloudwatch(query):
    log_group_name = '/aws/lambda/svc-tig-podaac-services-uat-hitide-backfill-lambda'
    response = client.start_query(
        logGroupName=log_group_name,
        startTime=int((time.time() - 1 * 3600) * 1000),  # Two hours ago
        endTime=int(time.time() * 1000),
        queryString=query,
        limit=10000
    )

    query_id = response['queryId']

    while True:
        query_status = client.get_query_results(queryId=query_id)
        status = query_status['status']
        if status == 'Complete':
            break
        elif status == 'Failed' or status == 'Cancelled':
            print("Query execution failed or was cancelled.")
            break
        time.sleep(1)

    return query_id

# Function to execute query with pagination
def execute_query_with_pagination(query, start_time, end_time):

    log_group_name = '/aws/lambda/svc-tig-podaac-services-uat-hitide-backfill-lambda'

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
        elif status == 'Failed' or status == 'Cancelled':
            print("Query execution failed or was cancelled.")
            break
        time.sleep(1)

    # Retrieve initial results
    results = client.get_query_results(
        queryId=query_id
    )

    data = results['results']

    return data


# Combined query
combined_query = """
fields @timestamp, @message
| filter (@message like /Max Memory Used:/ or @message like /aws_request_id/)
"""

# Function to execute query for a given minute
def execute_query_for_minute(query, minute_start_time, minute_end_time):
    results = execute_query_with_pagination(query, minute_start_time, minute_end_time)
    return results

# Function to execute query for a given time range, minute by minute
def execute_query_for_time_range(query, start_time, end_time):
    all_results = []
    current_time = start_time

    while current_time < end_time:
        minute_start_time = current_time
        minute_end_time = current_time + (300 * 1000)  # 1 minute interval
        results = execute_query_for_minute(query, minute_start_time, minute_end_time)
        all_results.extend(results)
        current_time = minute_end_time

    return all_results

# Compile regex patterns
request_id_pattern = re.compile(r"RequestId: (\S+)")
memory_used_pattern = re.compile(r"Max Memory Used: (\d+) MB")
billed_duration_pattern = re.compile(r"Billed Duration: (\d+) ms")

start_time=int((time.time() - 2.5 * 3600) * 1000)
end_time=int((time.time() - 1.5 * 3600) * 1000)
response = execute_query_for_time_range(combined_query, start_time, end_time)


# Process results
for result in response:
    text = result[1]['value']
    if 'aws_request_id' in text:
        json_message = json.loads(text).get('message')
        try:
            message = json.loads(json_message)
            request_id = message.get('aws_request_id')
            collection = message.get('collection')
            if request_id in request_collection:
                request_collection[request_id]["request_id"] = request_id
                request_collection[request_id]["collection"] = collection
            else:
                request_collection[request_id] = {
                    "request_id": request_id,
                    "collection": collection
                }
        except Exception as ex:
            pass

    elif 'Max Memory Used:' in text:
        request_id_match = request_id_pattern.search(text)
        memory_used_match = memory_used_pattern.search(text)
        billed_duration_match = billed_duration_pattern.search(text)
        if request_id_match and memory_used_match:
            request_id = request_id_match.group(1)
            memory_used = int(memory_used_match.group(1))
            billed_duration = int(billed_duration_match.group(1))
            if request_id in request_collection:
                request_collection[request_id]["memory_used"] = memory_used
                request_collection[request_id]["billed_duration"] = billed_duration
            else:
                request_collection[request_id] = {
                    "memory_used": memory_used,
                    "billed_duration": billed_duration
                }

for key, item in request_collection.items():

    collection = item.get('collection', None)
    memory = item.get('memory_used')
    billed_duration = item.get('billed_duration')
    if collection:
        if collection in memory_collection:
            memory_collection[collection].append(memory)
            billed_collection[collection].append(billed_duration)
        else:
            memory_collection[collection] = [memory]
            billed_collection[collection] = [billed_duration]

csv_filename = "collection_statistics2.csv"
header = ["Collection", "Mem Max", "Mem Min", "Mem Med", "Mem Avg", "Bill Max", "Bill Min", "Bill Med", "Bill Avg", "Sampled"]

with open(csv_filename, mode='w', newline='') as file:

    writer = csv.writer(file)
    writer.writerow(header)

    for key in sorted(memory_collection.keys()):

        item = memory_collection[key]
        _item = [x for x in item if x is not None]

        if len(item) == 0 or item is None:
            _item = [0]

        bill_item = billed_collection[key]
        _bill_item = [x for x in bill_item if x is not None]
        if len(bill_item) == 0 or bill_item is None:
            _bill_item = [0]

        collection = key
        minimum = min(_item)
        maximum = max(_item)
        sampled = len(_item)
        average = round(sum(_item) / sampled, 1)
        median = statistics.median(_item)

        bill_min = min(_bill_item)
        bill_max = max(_bill_item)
        bill_avg = round(sum(_bill_item) / sampled, 1)
        bill_med = statistics.median(_bill_item)

        row = [collection, maximum, minimum, median, average, bill_max, bill_min, bill_med, bill_avg, sampled]
        writer.writerow(row)

