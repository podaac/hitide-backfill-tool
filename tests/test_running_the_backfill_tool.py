import os
import pytest
from podaac.hitide_backfill_tool.cli import main
from moto.core import DEFAULT_ACCOUNT_ID
from moto.sns import sns_backends
from moto import mock_sns, mock_s3
import boto3
import json
from podaac.hitide_backfill_tool.file_util import make_absolute

#
#     Fixtures
#


@pytest.fixture(scope='function')
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-west-2'


@pytest.fixture(scope='function')
def sns(aws_credentials):
    with mock_sns():
        yield boto3.client('sns')


@pytest.fixture(scope='function')
def sns_topic(sns):
    response = sns.create_topic(Name="test")
    topic_arn = response['TopicArn']
    yield sns_backends[DEFAULT_ACCOUNT_ID]["us-west-2"].topics[topic_arn]


@pytest.fixture(scope='function')
def s3(aws_credentials):
    with mock_s3():
        yield boto3.client('s3')

@pytest.fixture(scope='function')
def s3_object(s3):

    # Create mock bucket
    bucket_name = 'podaac-uat-cumulus-protected'
    s3.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": "us-west-2"})

    # Upload a file to the bucket
    object_key = 'MODIS_A-JPL-L2P-v2019.0/20020704004505-JPL-L2P_GHRSST-SSTskin-MODIS_A-D-v02.0-fv01.0.nc.dmrpp'

    abs_path = make_absolute('resources/sample.nc.dmrpp', relative_to=__file__)
    with open(abs_path, 'rb') as f:
        s3.put_object(Bucket=bucket_name, Key=object_key, Body=f)

    yield s3

#
#     Tests
#
@mock_s3
@pytest.mark.e2e
def test_running_the_backfill_tool_will_send_a_message_to_an_sns_topic(sns_topic):
    cumulus_configurations_dir = make_absolute('resources/cumulus_configurations', relative_to=__file__)

    main(f"""
          -c MODIS_A-JPL-L2P-v2019.0
          --provider pocloud
          --cmr uat
          -sd 2002-07-04T00:00:00.000Z -ed 2002-07-04T01:00:00.000Z
          --use-data-url
          --message-limit 2
          --cumulus uat
          --sns-arn {sns_topic.arn}
          --log-level DEBUG
          --footprint force
          --image force
          --cumulus-configurations {cumulus_configurations_dir}
          --default_message_config "/test"
        """)

    # There should two messages for one granule. One for forge and one for tig
    notifications = sns_topic.sent_notifications
    assert len(notifications) == 2

    first_message = json.loads(notifications[0][1])
    assert bool(first_message.get('forge')) ^ bool(first_message.get("tig"))

    second_message = json.loads(notifications[1][1])
    assert bool(second_message.get('forge')) ^ bool(second_message.get("tig"))


@pytest.mark.skip(reason="Temporarily disabled")
@pytest.mark.e2e
def test_running_the_backfill_tool_for_dmrpp(s3_object, sns_topic):
    cumulus_configurations_dir = make_absolute('resources/cumulus_configurations', relative_to=__file__)

    main(f"""
      -c MODIS_A-JPL-L2P-v2019.0
      --provider pocloud
      --cmr uat
      --page-size 100
      -sd 2002-07-04T00:00:00.000Z -ed 2002-07-04T01:00:00.000Z
      --use-data-url
      --cumulus uat
      --sns-arn {sns_topic.arn}
      --log-level DEBUG
      --footprint off
      --image off
      --dmrpp on
      --dmrpp-min-version 3.20.9-91
      --cumulus-configurations {cumulus_configurations_dir}
      --default_message_config "/test"
    """)

    notifications = sns_topic.sent_notifications
    assert len(notifications) == 13

    first_message = json.loads(notifications[0][1])
    second_message = json.loads(notifications[1][1])

    assert bool(second_message.get('dmrpp'))
    assert bool(second_message.get("skip_cmr_opendap_update"))
    assert bool(first_message.get('dmrpp'))
    assert bool(first_message.get("skip_cmr_opendap_update")) == bool(False)
