resource "aws_ssm_parameter" "backfill_tool_deploy_metadata" {
  name  = "backfill_tool_metadata"
  type  = "String"
  value = jsonencode(var.backfill_tool_metadata)
}