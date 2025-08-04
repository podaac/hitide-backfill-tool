data "aws_ssm_parameter" "role_mappings" {
  name = "${local.resources_name}-role-mappings"
} 