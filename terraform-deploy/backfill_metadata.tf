resource "aws_ssm_parameter" "backfill_tool_deploy_metadata" {
  name  = "backfill_tool_metadata"
  type  = "String"
  value = join("\n", [for k, v in local.backfill_tool_metadata : "${k} = ${v}"])
}