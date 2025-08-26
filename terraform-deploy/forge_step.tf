resource "aws_sfn_state_machine" "forge" {
  name     = "${local.resources_name}-forge"
  role_arn = aws_iam_role.step.arn

  definition = <<EOF
{
  "Comment": "Footprint Processing",
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
      "Next": "FootprintChoice"
    },
    "FootprintChoice": {
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
          "Next": "FootprintBranchingFargate"
        }
      ],
      "Default": "FootprintBranching"
    },
    "FootprintBranching": {
      "Parameters": {
        "cma": {
          "event.$": "$",
          "task_config": {
            "execution_name": "{$.cumulus_meta.execution_name}",
            "collection": "{$.meta.collection}",
            "cumulus_message": {
              "input": "{$.payload}"
            }
          }
        }
      },
      "Type": "Task",
      "Resource": "${module.forge_py_module.forge_branch_task_lambda_arn}",
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
          "IntervalSeconds": 5,
          "MaxAttempts": 2
        }
      ],
      "Next": "FootprintBranchChoice"
    },
    "FootprintBranchingFargate": {
      "Parameters": {
        "cma": {
          "event.$": "$",
          "task_config": {
            "execution_name": "{$.cumulus_meta.execution_name}",
            "collection": "{$.meta.collection}",
            "cumulus_message": {
              "input": "{$.payload}"
            }
          }
        }
      },
      "Type": "Task",
      "Resource": "${module.forge_py_module.forge_branch_task_lambda_arn}",
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
          "IntervalSeconds": 5,
          "MaxAttempts": 2
        }
      ],
      "Next": "FootprintFargateBranchChoice"
    },
    "FootprintFargateBranchChoice": {
      "Type": "Choice",
      "Choices": [
        {
          "And": [
            {
              "Variable": "$.meta.collection.meta.workflowChoice.forge_version",
              "IsPresent": true
            },
            {
              "Variable": "$.meta.collection.meta.workflowChoice.forge_version",
              "StringEquals": "forge-py"
            }
          ],
          "Next": "ForgePyProcessFargate"
        }
      ],
      "Default": "FootprintProcessFargate"
    },
    "FootprintBranchChoice": {
      "Type": "Choice",
      "Choices": [
        {
          "And": [
            {
              "Variable": "$.meta.collection.meta.workflowChoice.forge_version",
              "IsPresent": true
            },
            {
              "Variable": "$.meta.collection.meta.workflowChoice.forge_version",
              "StringEquals": "forge-py"
            }
          ],
          "Next": "ForgePyProcess"
        }
      ],
      "Default": "ForgeProcess"
    },
    "ForgePyProcess": {
      "Parameters": {
        "cma": {
          "event.$": "$",
          "task_config": {
            "execution_name": "{$.cumulus_meta.execution_name}",
            "collection": "{$.meta.collection}",
            "requester_pay", true,
            "cumulus_message": {
              "input": "{$.payload}"
            }
          }
        }
      },
      "Type": "Task",
      "Resource": "${module.forge_py_module.forge_py_task_lambda_arn}",
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
          "IntervalSeconds": 5,
          "MaxAttempts": 2
        }
      ],
      "Next": "MetadataAggregator"
    },
    "ForgePyProcessFargate": {
      "Parameters": {
        "cma": {
          "event.$": "$",
          "task_config": {
            "execution_name": "{$.cumulus_meta.execution_name}",
            "collection": "{$.meta.collection}",
            "requester_pay", true,
            "cumulus_message": {
              "input": "{$.payload}"
            }
          }
        }
      },
      "Type": "Task",
      "Resource": "${module.forge_py_module.forge_py_ecs_task_id}",
      "TimeoutSeconds": 10800,
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
          "IntervalSeconds": 5,
          "MaxAttempts": 2
        }
      ],
      "Next": "MetadataAggregator"
    },
    "ForgeProcess": {
      "Parameters": {
        "cma": {
          "event.$": "$",
          "task_config": {
            "execution_name": "{$.cumulus_meta.execution_name}",
            "collection": "{$.meta.collection}",
            "cumulus_message": {
              "input": "{$.payload}",
              "outputs": [
                {
                  "source": "{$.input.granules}",
                  "destination": "{$.payload.granules}"
                }
              ]
            }
          }
        }
      },
      "Type": "Task",
      "Resource": "${module.forge_module.forge_task_arn}",
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
          "IntervalSeconds": 5,
          "MaxAttempts": 2
        }
      ],
      "Next": "MetadataAggregator"
    },
    "FootprintProcessFargate": {
      "Parameters": {
        "cma": {
          "event.$": "$",
          "task_config": {
            "execution_name": "{$.cumulus_meta.execution_name}",
            "collection": "{$.meta.collection}",
            "cumulus_message": {
              "input": "{$.payload}",
              "outputs": [
                {
                  "source": "{$.input.granules}",
                  "destination": "{$.payload.granules}"
                }
              ]
            }
          }
        }
      },
      "Type": "Task",
      "Resource": "${module.forge_module.forge_ecs_task_id}",
      "TimeoutSeconds": 10800,
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
          "IntervalSeconds": 5,
          "MaxAttempts": 2
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
            "stateMachine": "ForgeWorkflow",
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
      "Next": "FootprintChoice"
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
        "delaySeconds.$": "States.MathAdd($.delaySeconds, 223)",
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