resource "aws_ssm_parameter" "backfill_tool_deploy_metadata" {
  name  = "backfill_tool_metadata"
  type  = "String"
  value = var.backfill_tool_metadata
}