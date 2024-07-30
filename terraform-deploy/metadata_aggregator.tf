resource "aws_lambda_function" "metadata_aggregator_task" {
  function_name = "${local.resources_name}-MetadataAggregator"
  filename      = "metadata-aggregator.zip"
  source_code_hash = filebase64sha256("metadata-aggregator.zip")
  handler       = "gov.nasa.cumulus.metadata.aggregator.MetadataAggregatorHandler::handleRequestStreams"
  role          = aws_iam_role.iam_execution.arn
  runtime       = "java11"
  timeout       = 300
  memory_size   = 512

  layers = [aws_lambda_layer_version.cumulus_message_adapter.arn]
  environment {
    variables = {
      CMR_ENVIRONMENT             = var.cmr_environment
      stackName                   = local.resources_name
      CUMULUS_MESSAGE_ADAPTER_DIR = "/opt/"
      region                      = var.region
      LAUNCHPAD_CRYPTO_DIR        = "${local.resources_name}/crypto"
      LAUNCHPAD_TOKEN_BUCKET      = "${local.resources_name}-internal"
      LAUNCHPAD_TOKEN_FILE        = "${local.resources_name}/crypto/tva_token.json"
      CMR_URL                     = var.cmr_url
      INTERNAL_BUCKET             = "${local.resources_name}-internal"
      CMR_DIR                     = "CMR"
    }
  }

  vpc_config {
    subnet_ids = var.subnet_ids
    security_group_ids = var.security_group_ids
  }

  tags = merge(local.tags, { Project = local.resources_name })
}

resource "aws_cloudwatch_log_group" "metadata_aggregator_task" {
  name              = "/aws/lambda/${aws_lambda_function.metadata_aggregator_task.function_name}"
  retention_in_days = 7
  tags              = merge(local.tags, { Project = local.resources_name })
}
