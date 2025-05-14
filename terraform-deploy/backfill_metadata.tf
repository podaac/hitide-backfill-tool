# Read and decode the JSON file
locals {
  backfill_tool_metadata = jsondecode(file("${path.module}/backfill_tool_metadata.json"))
}

resource "aws_ssm_parameter" "backfill_tool_deploy_metadata" {
  name  = "backfill_tool_metadata"
  type  = "String"
  value = join("\n", [for k, v in local.backfill_tool_metadata : "${k} = ${v}"])
}