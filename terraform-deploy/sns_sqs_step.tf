data "aws_secretsmanager_secret" "secret_roles" {
  name = "backfill_tool_sns_permission_roles_secret"
}

data "aws_secretsmanager_secret_version" "secret_roles" {
  secret_id = data.aws_secretsmanager_secret.secret_roles.id
}

# Create some locals for SQS and SNS names
locals {
  secret_json = jsondecode(data.aws_secretsmanager_secret_version.secret_roles.secret_string)
  roles       = local.secret_json.roles
  sqs-name = "${local.resources_name}-sqs"
  sns-name = "${local.resources_name}-sns"
}

# Create a topic policy. This will allow for the SQS queue to be able to subscribe to the topic
data "aws_iam_policy_document" "sns-topic-policy" {
  statement {
    actions = [
      "SNS:Subscribe",
      "SNS:Receive",
    ]

    condition {
      test     = "StringEquals"
      variable = "SNS:Endpoint"

      values = [
        "arn:aws:sqs:${var.region}:${data.aws_caller_identity.current.account_id}:${local.sqs-name}",
      ]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:PrincipalAccount"
      values = [
        data.aws_caller_identity.current.account_id
      ]
    }

    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = [
        "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
      ]
    }

    resources = [
      "arn:aws:sns:${var.region}:${data.aws_caller_identity.current.account_id}:${local.sns-name}"
    ]

    sid = "AllowSQSSubscription"
  }

  statement {
    actions = [
      "SNS:Publish",
      "SNS:GetTopicAttributes"
    ]

    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = local.roles  # Use the roles from the secret
    }

    resources = [
      "arn:aws:sns:${var.region}:${data.aws_caller_identity.current.account_id}:${local.sns-name}"
    ]

    sid = "AllowSNSPublish"
  }

}

# Create a queue policy. This allows for the SNS topic to be able to publish messages to the SQS queue
data "aws_iam_policy_document" "sqs-queue-policy" {
  policy_id = "arn:aws:sqs:${var.region}:${data.aws_caller_identity.current.account_id}:${local.sqs-name}/SQSDefaultPolicy"

  statement {
    sid    = "example-sns-topic"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = ["*"]
    }

    actions = [
      "SQS:SendMessage",
    ]

    resources = [
      "arn:aws:sqs:${var.region}:${data.aws_caller_identity.current.account_id}:${local.sqs-name}"
    ]

    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"

      values = [
        "arn:aws:sns:${var.region}:${data.aws_caller_identity.current.account_id}:${local.sns-name}"
      ]
    }
  }
}

# Create the SNS topic and assign the topic policy to it
resource "aws_sns_topic" "sns-topic" {
  name         = local.sns-name
  display_name = local.sns-name
  policy       = data.aws_iam_policy_document.sns-topic-policy.json
}

resource "aws_sqs_queue" "sqs-dead-letter-queue" {
  name                      = "${local.resources_name}-hitide-backfill-dead-letter-queue"
  message_retention_seconds = 1209600
}

# Create the SQS queue and assign the queue policy to it
resource "aws_sqs_queue" "sqs-queue" {
  name   = local.sqs-name
  policy = data.aws_iam_policy_document.sqs-queue-policy.json
  visibility_timeout_seconds = var.message_visibility_timeout
  message_retention_seconds = 1209600

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.sqs-dead-letter-queue.arn
    maxReceiveCount     = var.step_retry
  })
  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue",
    sourceQueueArns   = [aws_sqs_queue.sqs-dead-letter-queue.arn]
  })

}

resource "aws_sns_topic_subscription" "sns_to_sqs" {
  topic_arn = aws_sns_topic.sns-topic.arn
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.sqs-queue.arn
}
