resource "aws_sfn_state_machine" "tig" {
  name     = "${local.resources_name}-tig"
  role_arn = aws_iam_role.step.arn

  definition = <<EOF
{
  "Comment": "Image Processing",
  "StartAt": "Normalizer",
  "TimeoutSeconds": 10800,
  "States": {
    "Normalizer": {
      "Parameters": {
        "cma": {
          "event.$": "$",
          "task_config": {
            "collection": "{$.meta.collection}"
          }    
        }
      },
      "Type": "Task",
      "Resource": "${module.postworkflow_normalizer_module.postworkflow_normalizer_arn}",
      "Catch": [
        {
          "ErrorEquals": [
            "States.ALL"
          ],
          "ResultPath": "$.exception",
          "Next": "WorkflowFailed"
        }
      ],
      "Retry": ${jsonencode(local.lambda_retry_policy)},
      "Next": "InitializeCounterDelay"
    },
    "InitializeCounterDelay": {
      "Type": "Pass",
      "Result": 0,
      "ResultPath": "$.delaySeconds",
      "Next": "ImageGeneratorChoice"
    },
    "ImageGeneratorChoice": {
      "Type": "Choice",
      "Choices": [
        {
          "And": [
            {
              "Variable": "$.meta.collection.meta.workflowChoice.ecs_lambda",
              "IsPresent": true
            },
            {
              "Variable": "$.meta.collection.meta.workflowChoice.ecs_lambda",
              "StringEquals": "ecs"
            }
          ],
          "Next": "ECSImageProcess"
        }
      ],
      "Default": "ImageProcess"
    },
    "ImageProcess": {
      "Parameters": {
        "cma": {
          "event.$": "$",
          "task_config": {
            "collection": "{$.meta.collection}",
            "buckets": "{$.meta.buckets}",
            "requester_pay": true,
            "cumulus_message": {
              "input": "{$.payload}"
            }
          }
        }
      },
      "Type": "Task",
      "Resource": "${module.tig.tig_task_lambda_arn}",
      "Catch": [
        {
          "ErrorEquals": [
            "States.ALL"
          ],
          "ResultPath": "$.exception",
          "Next": "WorkflowFailed"
        }
      ],
      "Retry": ${jsonencode(local.lambda_retry_policy)},
      "Next": "MetadataAggregator"
    },
    "ECSImageProcess": {
      "Parameters": {
        "cma": {
          "event.$": "$",
          "task_config": {
            "collection": "{$.meta.collection}",
            "buckets": "{$.meta.buckets}",
            "requester_pay": true,
            "cumulus_message": {
              "input": "{$.payload}"
            }
          }
        }
      },
      "Type": "Task",
      "TimeoutSeconds": 10800,
      "Resource": "${module.tig.tig_ecs_task_id}",
      "Catch": [
        {
          "ErrorEquals": [
            "States.ALL"
          ],
          "ResultPath": "$.exception",
          "Next": "WorkflowFailed"
        }
      ],
      "Retry": [
        {
          "ErrorEquals": [
            "States.ALL"
          ],
          "IntervalSeconds": 2,
          "MaxAttempts": 3
        }
      ],
      "Next": "MetadataAggregator"
    },
    "MetadataAggregator": {
      "Parameters": {
        "cma": {
          "event.$": "$",
          "task_config": {
            "internalBucket": "{$.meta.buckets.internal.name}",
            "publicBucket": "{$.meta.buckets.public.name}",
            "collection": "{$.meta.collection.name}",
            "version": "{$.meta.collection.version}",
            "granuleId": "{$.payload.granules[0].granuleId}",
            "distribution_endpoint": "{$.meta.distribution_endpoint}",
            "launchpadConfig": "{$.meta.launchpad}",
            "provider": "{$.meta.cmr.provider}",
            "systemBucket": "{$.cumulus_meta.system_bucket}",
            "executionId": "{$.cumulus_meta.execution_name}",
            "stateMachine": "ThumbnailImageWorkflow",
            "cumulus_message": {
              "input": "{$.payload.granules}",
              "outputs": [
                {
                  "source": "{$.output}",
                  "destination": "{$.payload.granules}"
                },
                {
                  "source": "{$.cmrRevisionId}",
                  "destination": "{$.payload.cmrRevisionId}"
                }
              ]
            }
          }
        }
      },
      "Type": "Task",
      "Resource": "${aws_lambda_function.metadata_aggregator_task.arn}",
      "Retry": ${jsonencode(local.lambda_retry_policy)},
      "Catch": [
        {
          "ErrorEquals": [
            "States.ALL"
          ],
          "ResultPath": "$.exception",
          "Next": "WorkflowFailed"
        }
      ],
      "Next": "CMAClean"
    },
    "CMAClean": {
      "Parameters": {
        "cma": {
          "event.$": "$",
          "task_config": {
            "cumulus_message": {
              "input": "{$.payload}"
            }
          }
        }
      },
      "Type": "Task",
      "TimeoutSeconds": 10800,
      "Resource": "${module.tig.tig_task_cleaner_lambda_arn}",
      "Catch": [
        {
          "ErrorEquals": [
            "States.ALL"
          ],
          "ResultPath": "$.exception",
          "Next": "WorkflowFailed"
        }
      ],
      "Retry": ${jsonencode(local.lambda_retry_policy)},
      "Next": "CmrStep"
    },
    "CmrStep": {
      "Parameters": {
        "cma": {
          "event.$": "$",
          "task_config": {
            "bucket": "{$.meta.buckets.internal.name}",
            "stack": "{$.meta.stack}",
            "granuleIdExtraction": "{$.meta.collection.granuleIdExtraction}",
            "cmr": "{$.meta.cmr}",
            "launchpad": "{$.meta.launchpad}",
            "input_granules": "{$.payload.granules}"
          }
        }
      },
      "Type": "Task",
      "Resource": "${aws_lambda_function.post_to_cmr_task.arn}",
      "Retry": ${jsonencode(local.lambda_retry_policy)},
      "Catch": [
        {
          "ErrorEquals": [
            "Error"
          ],
          "ResultPath": "$.cause",
          "Next": "CMRErrorPass"
        },
        {
          "ErrorEquals": [
            "States.ALL"
          ],
          "ResultPath": "$.exception",
          "Next": "WorkflowFailed"
        }
      ],
      "Next": "WorkflowSucceeded"
    },
    "delay": {
      "Type": "Wait",
      "SecondsPath": "$.delaySeconds",
      "Next": "MetadataAggregator"
    },
    "CMRErrorPass": {
      "Type": "Pass",
      "Parameters": {
        "cumulus_meta.$": "$.cumulus_meta",
        "meta.$": "$.meta",
        "payload.$": "$.payload",
        "task_config.$": "$.task_config",
        "cli_params.$": "$.cli_params",
        "sqs_data.$": "$.sqs_data",
        "skip_cmr_opendap_update.$": "$.skip_cmr_opendap_update",
        "delaySeconds.$": "States.MathAdd($.delaySeconds, 389)",
        "details.$": "States.StringToJson($.cause.Cause)"
      },
      "Next": "CMRErrorMessage"
    },
    "CMRErrorMessage": {
      "Type": "Choice",
      "Choices": [
        {
          "And": [
            {
              "Variable": "$.details.errorMessage",
              "StringMatches": "Failed to ingest, statusCode: 409, statusMessage: Conflict, CMR error message*"
            },
            {
              "Variable": "$.details.errorMessage",
              "IsPresent": true
            }
          ],
          "Next": "delay"
        }
      ],
      "Default": "WorkflowFailed"
    },
    "WorkflowSucceeded": {
      "Type": "Succeed"
    },
    "WorkflowFailed": {
      "Type": "Fail",
      "Cause": "Workflow failed"
    }
  }
}
EOF
}