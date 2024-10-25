module "forge_py_module" {
    source = "https://github.com/podaac/forge-py/releases/download/0.1.0/forge-py-terraform-0.1.0.zip"
    lambda_container_image_uri = "ghcr.io/podaac/forge-py:0.1.0"
    prefix = local.resources_name
    region = var.region
    cmr_environment = var.cmr_environment
    config_url = "https://hitide.podaac.earthdatacloud.nasa.gov/dataset-configs"
    footprint_output_bucket = "${local.resources_name}-internal"
    footprint_output_dir    = "dataset-metadata"
    lambda_role = aws_iam_role.iam_execution.arn
    security_group_ids = [var.aws_security_group_ids]
    subnet_ids = data.aws_subnets.private.ids
    memory_size = 1024
    timeout = 900
}
