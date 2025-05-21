# Check if the JSON file exists
locals {
  file_exists = fileexists("${path.module}/backfill_tool_metadata.json")
  backfill_tool_metadata = local.file_exists ? jsondecode(file("${path.module}/backfill_tool_metadata.json")) : {}
}

resource "aws_ssm_parameter" "backfill_tool_deploy_metadata" {
  name  = "backfill_tool_metadata"
  type  = "String"
  value = join("\n", [for k, v in local.backfill_tool_metadata : "${k} = ${v}"])
}