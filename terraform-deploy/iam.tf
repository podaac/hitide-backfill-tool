data "aws_caller_identity" "current" {}

data "aws_iam_policy_document" "iam_assume_role_policy" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com", "lambda.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "iam_policy" {

  statement {
    actions = [
       "logs:CreateLogGroup",
       "logs:CreateLogStream",
       "logs:DescribeLogStreams",
       "logs:PutLogEvents",

    ]
    resources = ["arn:aws:logs:*:${data.aws_caller_identity.current.account_id}:*"] 
  }

  statement {
    actions = [
       "dynamodb:DeleteItem",
       "dynamodb:GetItem",
       "dynamodb:PutItem",
       "dynamodb:UpdateItem",
    ]
    resources = ["arn:aws:dynamodb:*:${data.aws_caller_identity.current.account_id}:*"] 
  }

  statement {
    actions = [
       "sqs:ReceiveMessage",
       "sqs:SendMessage",
       "sqs:GetQueueAttributes",
       "sqs:DeleteMessage",
       "sqs:ChangeMessageVisibility"
    ]
    resources = ["arn:aws:sqs:*:${data.aws_caller_identity.current.account_id}:*"] 
  }

  statement {
    actions = [
       "states:StartExecution"
    ]
    resources = ["arn:aws:states:*:${data.aws_caller_identity.current.account_id}:*"] 
  }

  statement {
    actions = [
       "s3:GetObject*",
       "s3:PutObject*",
       "s3:DeleteObject",
       "s3:ListBucket*"
    ]
    resources = ["arn:aws:s3:::*"]
  }

  statement {
    actions = [
       "ec2:CreateNetworkInterface",
       "ec2:DeleteNetworkInterface",
       "ec2:DescribeInstances",
       "ec2:DescribeNetworkInterfaces"
    ]
    resources = ["*"]
  }

  statement {
    actions = ["ssm:*"]
    resources = ["*"]
  }

  statement {
    actions = ["secretsmanager:*"]
    resources = ["arn:aws:secretsmanager:*:${data.aws_caller_identity.current.account_id}:*"]
  }

  statement {
    actions = ["secretsmanager:GetSecretValue"]
    resources = ["*"]
  }

  statement {
    actions = ["secretsmanager:GetSecretValue"]
    resources = ["*"]
  }

  statement {
    actions = ["sts:AssumeRole"]
    resources = jsondecode(data.aws_ssm_parameter.role_mappings.value)
  }

}

resource "aws_iam_role" "iam_execution" {
  name                 = "${local.resources_name}_iam_execution_role"
  assume_role_policy   = data.aws_iam_policy_document.iam_assume_role_policy.json
  permissions_boundary = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/NGAPShRoleBoundary"
}

resource "aws_iam_role_policy" "policy_attachment" {
  name   = "${local.resources_name}_iam_role_policy"
  role   = aws_iam_role.iam_execution.id
  policy = data.aws_iam_policy_document.iam_policy.json
}
