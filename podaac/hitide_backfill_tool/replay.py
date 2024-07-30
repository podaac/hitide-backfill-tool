"""Script to get messages off dead letter queue and back into the queue"""

from argparse import ArgumentParser
import sys
import boto3
from podaac.hitide_backfill_tool.file_util import load_yaml_file


def replay(profile, dlq_url, sqs_url):
    """Function to get messages off dead letter queue to the sqs"""

    # Create a Boto3 session with the specified profile
    session = boto3.Session(profile_name=profile)

    # Create an SQS client using the session
    sqs = session.client('sqs')

    # Retrieve and move messages from the DLQ to the regular queue
    while True:
        response = sqs.receive_message(
            QueueUrl=dlq_url,
            MaxNumberOfMessages=1,  # Number of messages to retrieve at a time
        )
        messages = response.get('Messages', [])

        if not messages:
            break

        for message in messages:
            # Send the message back to the regular queue
            sqs.send_message(QueueUrl=sqs_url, MessageBody=message['Body'])

            # Delete the message from the DLQ
            sqs.delete_message(QueueUrl=dlq_url, ReceiptHandle=message['ReceiptHandle'])


def main(args=None):
    """main function to get arguments and call replay functions"""

    if args is None:
        args = sys.argv[1:]
    elif isinstance(args, str):
        args = args.split()

    parser = ArgumentParser()
    parser.add_argument("--config", required=True)

    args = parser.parse_args(args)

    config = load_yaml_file(args.config)

    aws_profile = config.get('aws_profile')
    dlq_url = config.get('dlq_url')
    sqs_url = config.get('sqs_url')

    if aws_profile is None or dlq_url is None or sqs_url is None:
        print("Please include aws_profile, dlq_url, and sqs_url in the config")
    else:
        replay(aws_profile, dlq_url, sqs_url)


if __name__ == "__main__":
    main()
