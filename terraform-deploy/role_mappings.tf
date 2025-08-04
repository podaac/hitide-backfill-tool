resource "aws_ssm_parameter" "role_mappings" {
  name      = "${local.resources_name}-role-mappings"
  type      = "String"
  value     = "{}"
  tags      = local.default_tags
} 