resource "aws_sfn_state_machine" "dmrpp" {
  name     = "${local.resources_name}-dmrpp"
  role_arn = aws_iam_role.step.arn

  definition = <<EOF
{
  "Comment": "DMRPP Processing",
  "StartAt": "Normalizer",
  "TimeoutSeconds": 10800,
  "States": {
    "Normalizer": {
      "Parameters": {
        "cma": {
          "event.$": "$",
          "task_config": {
            "collection": "{$.meta.collection}",
            "lambda_ephemeral_storage": 4294967296
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
      "Retry": [
        {
          "ErrorEquals": [
            "States.ALL"
          ],
          "IntervalSeconds": 2,
          "MaxAttempts": 3
        }
      ],
      "Next": "InitializeCounterDelay"
    },
    "InitializeCounterDelay": {
      "Type": "Pass",
      "Result": 0,
      "ResultPath": "$.delaySeconds",
      "Next": "DMRPP_ECS_LAMBDA_CHOICE"
    },
    "DMRPP_ECS_LAMBDA_CHOICE": {
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
              "StringEquals": "lambda"
            }
          ],
          "Next": "HyraxProcessingLambda"
        }
      ],
      "Default": "HyraxProcessing"
    },
    "HyraxProcessingLambda": {
      "Parameters": {
        "cma": {
          "event.$": "$",
          "task_config": {
            "buckets": "{$.meta.buckets}",
            "distribution_endpoint": "{$.meta.distribution_endpoint}",
            "files_config": "{$.meta.collection.files}",
            "fileStagingDir": "{$.meta.collection.name}",
            "granuleIdExtraction": "{$.meta.collection.granuleIdExtraction}",
            "collection": "{$.meta.collection}"
          }
        }
      },
      "Type": "Task",
      "Resource": "${module.dmrpp-generator.dmrpp_lambda_arn}",
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
      "Next": "DID DMRPP GENERATE?"
    },
    "HyraxProcessing": {
      "Parameters": {
        "cma": {
          "event.$": "$",
          "task_config": {
            "buckets": "{$.meta.buckets}",
            "distribution_endpoint": "{$.meta.distribution_endpoint}",
            "files_config": "{$.meta.collection.files}",
            "fileStagingDir": "{$.meta.collection.name}",
            "granuleIdExtraction": "{$.meta.collection.granuleIdExtraction}",
            "collection": "{$.meta.collection}"
          }
        }
      },
      "Type": "Task",
      "TimeoutSeconds": 43200,
      "Resource": "${module.dmrpp-generator.dmrpp_task_id}",
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
      "Next": "DID DMRPP GENERATE?"
    },
     "DID DMRPP GENERATE?":{  
       "Type": "Choice",
       "InputPath": "$",
       "OutputPath": "$",
       "Default": "WorkflowFailed",
       "Choices":[
         {
            "Variable": "$.payload.granules[0].files[1].fileName",
            "IsPresent": true,
            "Next": "DMRPP_Update_Choice"
         }
       ]
    },
    "DMRPP_Update_Choice": {
      "Type": "Choice",
      "Choices": [
        {
          "And": [
            {
              "Variable": "$.skip_cmr_opendap_update",
              "IsPresent": true
            },
            {
              "Variable": "$.skip_cmr_opendap_update",
              "BooleanEquals": true
            }
          ],
          "Next": "WorkflowSucceeded"
        }
      ],
      "Default": "MetadataAggregator"
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
            "stateMachine": "DMRPPWorkflow",
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
                },
                {
                  "source": "{$.cmrRevisionId}",
                  "destination": "{$.meta.cmrRevisionId}"
                }
              ]
            }
          }
        }
      },
      "Type": "Task",
      "Resource": "${aws_lambda_function.metadata_aggregator_task.arn}",
      "Retry": [
        {
          "ErrorEquals": [
            "States.ALL"
          ],
          "IntervalSeconds": 5,
          "MaxAttempts": 3
        }
      ],
      "Catch": [
        {
          "ErrorEquals": [
            "States.ALL"
          ],
          "ResultPath": "$.exception",
          "Next": "WorkflowFailed"
        }
      ],
      "Next": "HyraxMetadataUpdates"
    },
    "HyraxMetadataUpdates": {
      "Parameters": {
        "cma": {
          "event.$": "$",
          "task_config": {
            "buckets": "{$.meta.buckets}",
            "cmr": "{$.meta.cmr}",
            "launchpad": "{$.meta.launchpad}",
            "stack": "{$.meta.stack}"
          }
        }
      },
      "Type": "Task",
      "Resource": "${aws_lambda_function.hyrax_metadata_updates_task.arn}",
      "Retry": [
        {
          "BackoffRate": 2,
          "ErrorEquals": [
            "Lambda.ServiceException",
            "Lambda.AWSLambdaException",
            "Lambda.SdkClientException",
            "HTTPError"
          ],
          "IntervalSeconds": 15,
          "MaxAttempts": 6
        }
      ],
      "Catch": [
        {
          "ErrorEquals": [
            "States.ALL"
          ],
          "ResultPath": "$.exception",
          "Next": "WorkflowFailed"
        }
      ],
      "Next": "RevertRevisionId"
    },
    "RevertRevisionId": {
      "Type": "Pass",
      "Parameters": {
        "granules.$": "$.payload.granules",
        "cmrRevisionId.$": "$.meta.cmrRevisionId",
        "etags.$": "$.payload.etags"
      },
      "ResultPath": "$.payload",
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
      "Retry": [
        {
          "BackoffRate": 2,
          "ErrorEquals": [
            "States.ALL"
          ],
          "IntervalSeconds": 2,
          "MaxAttempts": 4
        }
      ],
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
      "Next": "HyraxProcessing"
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
        "delaySeconds.$": "States.MathAdd($.delaySeconds, 123)",
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