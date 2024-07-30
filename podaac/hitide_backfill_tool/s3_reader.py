"""Read files from S3"""

from urllib.parse import urlparse
import multiprocessing
from botocore.client import Config
from botocore.exceptions import ClientError
import boto3


class S3Reader:
    """Read files from S3"""

    def __init__(self, logger, aws_profile):
        """Create S3Reader"""
        logger.info("Checking S3 settings")
        config = Config(max_pool_connections=multiprocessing.cpu_count() * 4)
        if aws_profile:
            self.client = boto3.session.Session(
                profile_name=aws_profile).client('s3', config=config)
        else:
            self.client = boto3.client('s3', config=config)

        self.logger = logger

        # check access to s3
        try:
            self.client.list_buckets()
            logger.debug("S3Reader able to access S3")
        except ClientError as exc:
            raise Exception("S3Reader couldn't connect to S3") from exc

    def extract_bucket_and_file(self, s3_path):
        """Returns bucket_name and key from s3 path."""

        url = urlparse(s3_path, allow_fragments=False)
        return url.netloc, url.path.lstrip('/')

    def read_file_from_s3(self, s3_path):
        """Returns contents of file from S3 path. Assumes contents are in ISO-8859-1 encoding."""

        try:
            bucket_name, file_name = self.extract_bucket_and_file(s3_path)
            response = self.client.get_object(Bucket=bucket_name, Key=file_name)

            return response["Body"].read().decode("ISO-8859-1")
        except ClientError as exc:
            raise Exception(f"S3Reader could not read file at {s3_path}.") from exc
