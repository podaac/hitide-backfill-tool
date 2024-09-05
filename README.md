# hitide-backfill-tool

Tool to backfill thumbnail images and footprints for POCLOUD datasets

Some granules have been ingested without creating footprints/thumbnail images. The purpose of this tool is to trigger part of Cumulus workflow to generate footprints and images for granules that need it.

## What it does in a nutshell

- You specify search parameters at command line (collection, start_date, end_date, footprint, image, etc)
- Backfill-Tool searches CMR for matching granules
- Backfill-Tool figures out if the granule needs a footprint or image
- If footprint or image generation is needed, Backfill-Tool creates a Cumulus message and sends it to an AWS SNS topic.
- From there, another service will run trigger Forge/TIG and update CMR with new images/footprints as needed

## Prerequisites

- Python > 3.10
- poetry

## failed_workflow.py

- Script used to scan failed workflows and get unique errors
- Takes in three arguments
    - workflow_arn: arn of aws workflow
    - profile_name: aws profile name credential to use
    - limit: how many of latest execution to scan if not specified will go through all failed executions
- ex: python failed_workflow.py --workflow_arn arn:aws:states:us-west-2:123456:stateMachine:podaac-services-ops-hitide-backfill-forge --profile_name service_ops --limit 1000


## replay.py
- Script used to get messages off dead letter queue and back into regular queue
- Takes 1 argument
    - config: configuration that has the aws_profile, dlq_url, and sqs_url
- ex: replay --config config.cfg

## regression.py
- Script to run backfill tool command on all collection that has a forge-tig configuartion file
- Script can be modify to exclude or test specific collections

## memory_profiler.py
- Script to run profile the memory use of lambdas, currently only tig is being profiled
- Lambdas need to be modified to include lambda request id in cloudwatch logs
- Modify script with cloudwatch lambda to profile
- Modify script to include start time and end time range where cloudwatch events were logged

## ECS facility

- ECS template to start docker : ecs_cluster_instance_autoscaling_cf_template.yml.tmpl
- ECS script to execute task : task-reaper.sh
- All ECS related resources are specified in ecs_cluster.tf
- ECS is a cluster of EC2 instances.  While creating the EC2 instances, a key is given to create each EC2 and the key name is specified as key_name variable within variables.tf.   At this moment, the following keys are specified for each environment
    - backfill-tool-sit-cluster-keypair  (SIT)
    - backfill-tool-uat-cluster-keypair  (UAT)
    - backfill-tool-ops-cluster-keypair  (OPS)