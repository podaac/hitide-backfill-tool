data "aws_iam_policy_document" "ec2_assume_role_policy" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}


resource "aws_iam_role" "ecs_cluster_instance" {
  name = "${var.prefix}_ecs_cluster_instance_role"
  assume_role_policy   = data.aws_iam_policy_document.ec2_assume_role_policy.json
  permissions_boundary = var.permissions_boundary_arn

  tags = var.default_tags
}

data "aws_iam_policy_document" "ecs_cluster_instance_policy" {


  statement {
    actions = [
      "autoscaling:CompleteLifecycleAction",
      "autoscaling:DescribeAutoScalingInstances",
      "autoscaling:DescribeLifecycleHooks",
      "autoscaling:RecordLifecycleActionHeartbeat",
      "cloudwatch:GetMetricStatistics",
      "ec2:DescribeInstances",
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
      "lambda:GetFunction",
      "lambda:GetLayerVersion",
      "lambda:invokeFunction",
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:DescribeLogStreams",
      "logs:PutLogEvents",
      "ssm:GetParameter"
    ]
    resources = ["*"]
  }

  statement {
    actions = [
      "kinesis:describeStream",
      "kinesis:ListShards",
      "kinesis:getShardIterator",
      "kinesis:GetRecords"
    ]
    resources = ["arn:aws:kinesis:*:*:*"]
  }

  statement {
    actions = [
      "sqs:Send*",
      "sqs:GetQueueUrl",
    ]
    resources = ["arn:aws:sqs:*:*:*"]
  }

  statement {
    actions = [
      "states:DescribeActivity",
      "states:DescribeExecution",
      "states:GetActivityTask",
      "states:GetExecutionHistory",
      "states:SendTaskFailure",
      "states:SendTaskSuccess"
    ]
    resources = ["arn:aws:states:*:*:*"]
  }

  statement {
    actions = [
      "s3:GetAccelerateConfiguration",
      "s3:GetBucket*",
      "s3:GetLifecycleConfiguration",
      "s3:GetReplicationConfiguration",
      "s3:ListBucket*",
      "s3:PutAccelerateConfiguration",
      "s3:PutBucket*",
      "s3:PutLifecycleConfiguration",
      "s3:PutReplicationConfiguration"
    ]
    resources = [for b in local.all_bucket_names : "arn:aws:s3:::${b}"]
  }

  statement {
    actions = [
      "s3:AbortMultipartUpload",
      "s3:DeleteObject",
      "s3:DeleteObjectVersion",
      "s3:GetObject*",
      "s3:ListMultipartUploadParts",
      "s3:PutObject*"
    ]
    resources = [for b in local.all_bucket_names : "arn:aws:s3:::${b}/*"]
  }

}

resource "aws_iam_role_policy" "ecs_cluster_instance" {
  name   = "${var.prefix}_ecs_cluster_instance_policy"
  role   = aws_iam_role.ecs_cluster_instance.id
  policy = data.aws_iam_policy_document.ecs_cluster_instance_policy.json
}

resource "aws_iam_role_policy_attachment" "NGAPProtAppInstanceMinimalPolicy" {
  count = var.deploy_to_ngap ? 1 : 0
  policy_arn = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/NGAPProtAppInstanceMinimalPolicy"
  role = aws_iam_role.ecs_cluster_instance.id
}
resource "aws_iam_instance_profile" "ecs_cluster_instance" {
  name = "${var.prefix}_ecs_cluster_profile"
  role = aws_iam_role.ecs_cluster_instance.id
}

resource "aws_security_group" "ecs_cluster_instance" {
  vpc_id = data.aws_vpc.default.id
  tags   = var.default_tags
}

resource "aws_security_group_rule" "ecs_cluster_instance_allow_ssh" {
  type              = "ingress"
  from_port         = 2
  to_port           = 2
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.ecs_cluster_instance.id
}

resource "aws_security_group_rule" "ecs_cluster_instance_allow_egress" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.ecs_cluster_instance.id
}

resource "aws_s3_object" "task_reaper" {
  bucket = var.system_bucket
  key    = "${var.prefix}/task-reaper.sh"
  source = "${path.module}/task-reaper.sh"
  etag   = filemd5("task-reaper.sh")
  tags   = var.default_tags
}

resource "aws_ecs_cluster" "default" {
  name = "${var.prefix}-CumulusECSCluster"
  tags = var.default_tags
}

data "aws_efs_mount_target" "ecs_cluster_instance" {
  count           = var.ecs_efs_config == null ? 0 : 1
  mount_target_id = var.ecs_efs_config.mount_target_id
}

locals {
  ecs_instance_autoscaling_cf_template_config = {
    cluster_name              = aws_ecs_cluster.default.name
    container_stop_timeout    = var.ecs_container_stop_timeout,
    docker_hub_config         = var.ecs_docker_hub_config,
    docker_storage_driver     = var.ecs_docker_storage_driver,
    docker_volume_size        = var.ecs_cluster_instance_docker_volume_size,
    docker_volume_create_size = var.ecs_cluster_instance_docker_volume_size - 1,
    efs_dns_name              = var.ecs_efs_config == null ? null : data.aws_efs_mount_target.ecs_cluster_instance[0].dns_name,
    efs_mount_point           = var.ecs_efs_config == null ? null : var.ecs_efs_config.mount_point,
    image_id                  = data.aws_ssm_parameter.ecs_image_id.value,
    include_docker_cleanup_cronjob = var.ecs_include_docker_cleanup_cronjob,
    instance_profile          = aws_iam_instance_profile.ecs_cluster_instance.arn,
    instance_type             = var.ecs_cluster_instance_type,
    key_name                  = var.key_name,
    min_size                  = var.ecs_cluster_min_size,
    desired_capacity          = var.ecs_cluster_desired_size,
    max_size                  = var.ecs_cluster_max_size,
    region                    = data.aws_region.current.name
    security_group_ids        = compact(concat(
      [
        aws_security_group.ecs_cluster_instance.id
      ],
      var.ecs_custom_sg_ids
    ))
    subnet_ids                = data.aws_subnets.private.ids,
    task_reaper_object        = aws_s3_object.task_reaper
  }
  all_bucket_names = [for k, v in var.buckets : v.name]
}

resource "aws_cloudformation_stack" "ecs_instance_autoscaling_group" {
  name          = "${aws_ecs_cluster.default.name}-autoscaling-group"
  template_body = templatefile("${path.module}/ecs_cluster_instance_autoscaling_cf_template.yml.tmpl", local.ecs_instance_autoscaling_cf_template_config)
  tags          = var.default_tags
}

# image type for ECS' EC2
data "aws_ssm_parameter" "ecs_image_id" {
  name = "image_id_ecs_amz2"
}
