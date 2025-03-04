resource "aws_lambda_function" "hyrax_metadata_updates_task" {
  function_name    = "${var.prefix}-HyraxMetadataUpdates"
  filename         = "hyrax-metadata-updates.zip"
  source_code_hash = filebase64sha256("hyrax-metadata-updates.zip")
  handler          = "index.handler"
  role             = aws_iam_role.iam_execution.arn
  runtime          = var.cumulus_node_version
  timeout          = 300
  memory_size      = 512

  layers = [aws_lambda_layer_version.cumulus_message_adapter.arn]

  environment {
    variables = {
      CMR_ENVIRONMENT             = var.cmr_environment
      CMR_HOST                    = var.cmr_custom_host
      stackName                   = local.resources_name
      system_bucket               = "${local.resources_name}-internal"
      CUMULUS_MESSAGE_ADAPTER_DIR = "/opt/"
    }
  }

  vpc_config {
    subnet_ids = data.aws_subnets.private.ids
    security_group_ids = [var.aws_security_group_ids]
  }
}