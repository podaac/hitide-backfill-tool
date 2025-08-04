resource "aws_ecs_cluster" "main" {
  name = "${var.prefix}-fargate-ecs-cluster"
}

data "aws_iam_policy_document" "fargate_assume_role_policy" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "fargate_policy" {

  statement {
    actions = [
       "autoscaling:CompleteLifecycleAction",
       "autoscaling:DescribeAutoScalingInstances",
       "autoscaling:DescribeLifecycleHooks",
       "autoscaling:RecordLifecycleActionHeartbeat",
       "cloudformation:DescribeStacks",
       "cloudwatch:GetMetricStatistics",
       "dynamodb:ListTables",
       "ec2:CreateNetworkInterface",
       "ec2:DeleteNetworkInterface",
       "ec2:DescribeInstances",
       "ec2:DescribeNetworkInterfaces",
       "ecr:BatchCheckLayerAvailability",
       "ecr:BatchGetImage",
       "ecr:GetAuthorizationToken",
       "ecr:GetDownloadUrlForLayer",
       "ecs:DeregisterContainerInstance",
       "ecs:DescribeClusters",
       "ecs:DescribeContainerInstances",
       "ecs:DescribeServices",
       "ecs:DiscoverPollEndpoint",
       "ecs:ListContainerInstances",
       "ecs:ListServices",
       "ecs:ListTaskDefinitions",
       "ecs:ListTasks",
       "ecs:Poll",
       "ecs:RegisterContainerInstance",
       "ecs:RunTask",
       "ecs:StartTelemetrySession",
       "ecs:Submit*",
       "ecs:UpdateContainerInstancesState",
       "events:DeleteRule",
       "events:DescribeRule",
       "events:DisableRule",
       "events:EnableRule",
       "events:ListRules",
       "events:PutRule",
       "kinesis:DescribeStream",
       "kinesis:GetRecords",
       "kinesis:GetShardIterator",
       "kinesis:ListStreams",
       "kinesis:PutRecord",
       "lambda:GetFunction",
       "lambda:GetLayerVersion",
       "lambda:invokeFunction",
       "logs:CreateLogGroup",
       "logs:CreateLogStream",
       "logs:DescribeLogStreams",
       "logs:PutLogEvents",
       "s3:ListAllMyBuckets",
       "sns:List*",
       "sns:publish",
       "ssm:GetParameter",
       "states:DescribeActivity",
       "states:DescribeExecution",
       "states:GetActivityTask",
       "states:GetExecutionHistory",
       "states:ListStateMachines",
       "states:SendTaskFailure",
       "states:SendTaskSuccess",
       "states:StartExecution",
       "states:StopExecution"
    ]
    resources = ["*"]
  }

  statement {
    actions = [
       "s3:AbortMultipartUpload",
       "s3:DeleteObject",
       "s3:DeleteObjectVersion",
       "s3:GetAccelerateConfiguration",
       "s3:GetBucket*",
       "s3:GetLifecycleConfiguration",
       "s3:GetObject*",
       "s3:GetReplicationConfiguration",
       "s3:ListBucket*",
       "s3:ListMultipartUploadParts",
       "s3:PutAccelerateConfiguration",
       "s3:PutBucket*",
       "s3:PutLifecycleConfiguration",
       "s3:PutObject*",
       "s3:PutReplicationConfiguration"
    ]
    resources = ["arn:aws:s3:::*"]
  }

  statement {
    actions = [
      "sqs:SendMessage",
      "sqs:ReceiveMessage",
      "sqs:ChangeMessageVisibility",
      "sqs:DeleteMessage",
      "sqs:GetQueueUrl",
      "sqs:GetQueueAttributes",
    ]
    resources = ["arn:aws:sqs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:*"]
  }

  statement {
    actions = ["sts:AssumeRole"]
    resources = ${data.aws_ssm_parameter.role_mappings.value}
  }

}

resource "aws_iam_role" "fargate_execution" {
  name               = "${local.resources_name}-fargate_execution-role"
  assume_role_policy = data.aws_iam_policy_document.fargate_assume_role_policy.json
  permissions_boundary = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/NGAPShRoleBoundary"
}

resource "aws_iam_role_policy" "fargate_policy_attachment" {
  name   = "${var.prefix}_fargate_ecs_cluster_instance_policy"
  role   = aws_iam_role.fargate_execution.id
  policy = data.aws_iam_policy_document.fargate_policy.json
}