data "aws_ssm_parameter" "role_mappings" {
  name = "${local.resources_name}-role-mappings"
} 


data "aws_ssm_parameter" "assume_role_list" {
  name = "${local.resources_name}-assume-role-list"
} 