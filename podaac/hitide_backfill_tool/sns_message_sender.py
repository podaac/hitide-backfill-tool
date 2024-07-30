"""Send messages to a file or SNS"""

import sys
import logging
import multiprocessing
from botocore.client import Config
from botocore.exceptions import ClientError
import boto3

from podaac.hitide_backfill_tool.file_util import make_absolute


class SnsMessageSender:
    """Send messages to SNS"""

    name = "sns"

    def __init__(self, topic_arn, logger, aws_profile):
        """Create SnsMessageSender"""
        logger.info("Checking SNS settings")
        config = Config(max_pool_connections=multiprocessing.cpu_count() * 4)
        if aws_profile:
            self.client = boto3.session.Session(
                profile_name=aws_profile).client('sns', config=config)
        else:
            self.client = boto3.client('sns', config=config)

        # check access to sns
        try:
            self.client.list_topics()
            logger.debug("SnsMessageSender able to connect to SNS")
        except ClientError as exc:
            raise Exception("SnsMessageSender couldn't connect to SNS") from exc

        # check "connection" to sns topic
        try:
            self.client.get_topic_attributes(
                TopicArn=topic_arn
            )
            logger.debug(
                f"SnsMessageSender able to access SNS topic: {topic_arn}")
        except ClientError as exc:
            raise Exception(
                f"SnsMessageSender given invalid topic_arn: {topic_arn}") from exc

        self.topic_arn = topic_arn
        self.logger = logger
        self.messages_sent = 0

    def send(self, message):
        """Send message to SNS topic"""
        try:
            self.client.publish(
                TopicArn=self.topic_arn,
                Message=message
            )
            self.messages_sent += 1
        except ClientError as exc:
            self.logger.error(f"""
      SNS Message Sender Failure
      {exc}
      -------------
      {message}
      """)

    def close(self):
        """Release resources"""


class FileMessageSender:
    """Send messages to file"""

    name = "file"
    messages_sent = 0

    def __init__(self, filename=None, logger=logging):
        """Create FileMessageSender"""
        self.logger = logger

        if filename is None:
            self.file = None

        elif filename == "stdout":
            self.file = sys.stdout

        else:
            abs_path = make_absolute(filename)
            # pylint: disable=consider-using-with; need file to stay open for lifetime of object
            self.file = open(abs_path, 'a', encoding="utf-8")

    def send(self, message):
        """Send message to file"""
        if not self.file:
            return
        self.file.write(f"\n{message}\n")
        self.messages_sent += 1

    def close(self):
        """Release resources"""
        if self.file and self.file != sys.stdout:
            self.file.close()
