resource "aws_lambda_function" "post_to_cmr_task" {
  function_name    = "${local.resources_name}-PostToCmr"
  filename         = "post_to_cmr.zip"
  handler          = "index.handler"
  role             = aws_iam_role.iam_execution.arn
  runtime          = "nodejs16.x"
  timeout          = 300
  memory_size      = 512

  layers = [aws_lambda_layer_version.cumulus_message_adapter.arn]

  vpc_config {
    subnet_ids = var.subnet_ids
    security_group_ids = var.security_group_ids
  }

  environment {
    variables = {
      CMR_ENVIRONMENT             = var.cmr_environment
      CMR_HOST                    = var.cmr_custom_host
      stackName                   = local.resources_name
      system_bucket               = "${local.resources_name}-internal"
      CUMULUS_MESSAGE_ADAPTER_DIR = "/opt/"
    }
  }

  tags = {
    Version = "18.2.0"
  }

}
