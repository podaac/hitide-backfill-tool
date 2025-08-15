locals {
  system_iam_role_name = "${local.system_prefix}-ec2-role"
}

data "aws_iam_role" "ec2" {
  name = local.system_iam_role_name
}

data "aws_iam_policy_document" "hitide_backfill_tools" {
  statement {
    sid = "AllowS3ReadOnly"
    actions = [
      "s3:GetObject",
      "s3:ListBucket"
    ]
    resources = var.protected_bucket_permission
  }

  statement {
    sid = "AllowListAllBuckets"
    actions = [
      "s3:ListAllMyBuckets"
    ]
    resources = ["*"]
  }

  statement {
    sid = "SNSPermissions"
    actions = [
      "sns:Publish",
      "sns:GetTopicAttributes"
    ]
    resources = var.sns_backfill_arns
  }
}

resource "aws_iam_role_policy" "hitide_backfill_tools" {
  name_prefix = "hitide-backfill-tools-Policy"
  role = data.aws_iam_role.ec2.name
  policy = data.aws_iam_policy_document.hitide_backfill_tools.minified_json
}