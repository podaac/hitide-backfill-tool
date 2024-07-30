module "postworkflow_normalizer_module" {

    source = "https://github.com/podaac/cumulus-postworkflow-normalizer/releases/download/0.4.0/postworkflow-normalizer-0.4.0.zip"
    prefix = local.resources_name
    region = var.region
    aws_profile = var.profile
    lambda_role = aws_iam_role.iam_execution.arn
    security_group_ids = var.security_group_ids
    subnet_ids = var.subnet_ids
    memory_size = 128
    timeout = 180

}
