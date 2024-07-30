locals {
  post-sqs-name = "${local.resources_name}-post-step-sqs"
}

resource "aws_cloudwatch_event_rule" "state_machine_execution_rule" {
  name = "${local.resources_name}-cloudwatch-rule"
  event_pattern = jsonencode({
    source      = ["aws.states"]
    detail-type = ["Step Functions Execution Status Change"]
    detail = {
      status = [
        "FAILED",
        "SUCCEEDED"
      ],
      stateMachineArn = [aws_sfn_state_machine.forge.id, aws_sfn_state_machine.tig.id, aws_sfn_state_machine.dmrpp.id]
    }
  })
}

resource "aws_sqs_queue" "post-step-dead-letter-queue" {
  name                      = "${local.resources_name}-post-step-dead-letter-queue"
  message_retention_seconds = 1209600
}

# Create the SQS queue and assign the queue policy to it
resource "aws_sqs_queue" "post-step-queue" {
  name   = local.post-sqs-name
  visibility_timeout_seconds = 900

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.post-step-dead-letter-queue.arn
    maxReceiveCount     = 3
  })

  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue",
    sourceQueueArns   = [aws_sqs_queue.post-step-dead-letter-queue.arn]
  })

}

resource "aws_lambda_event_source_mapping" "post_step_event_source_mapping" {
  event_source_arn = aws_sqs_queue.post-step-queue.arn
  enabled          = true
  function_name    = module.backfill_lambdas.backfill_post_step_task_arn
  batch_size       = 1
}

resource "aws_cloudwatch_event_target" "cloudwatch_event_target" {
  rule       = aws_cloudwatch_event_rule.state_machine_execution_rule.name
  arn        = aws_sqs_queue.post-step-queue.arn
}

data "aws_iam_policy_document" "sqs_from_cloudwatch_event" {
  statement {
    sid     = "AllowQueueFromCloudwatchEvent"
    actions = ["sqs:SendMessage"]
    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }
    resources = [aws_sqs_queue.post-step-queue.arn]

    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"

      values = [aws_cloudwatch_event_rule.state_machine_execution_rule.arn]
    }
  }
}

resource "aws_sqs_queue_policy" "post_sqs" {
  queue_url = aws_sqs_queue.post-step-queue.id
  policy    = data.aws_iam_policy_document.sqs_from_cloudwatch_event.json
}