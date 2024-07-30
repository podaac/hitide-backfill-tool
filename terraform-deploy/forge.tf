module "forge_module" {
    
    source = "https://github.com/podaac/forge/releases/download/0.11.0-rc.2/forge-0.11.0-rc.2.zip"
    prefix = local.resources_name
    region = var.region
    cmr_environment = var.cmr_environment
    config_url = "https://hitide.podaac.earthdatacloud.nasa.gov/dataset-configs"
    footprint_output_bucket = "${local.resources_name}-internal"
    footprint_output_dir    = "dataset-metadata"
    lambda_role = aws_iam_role.iam_execution.arn
    layers = [aws_lambda_layer_version.cumulus_message_adapter.arn]
    security_group_ids = [aws_security_group.lambda_sg.id]
    subnet_ids = data.aws_subnets.private.ids
    memory_size = 512
    timeout = 900
    profile = var.profile

    # ECS Variables
    cluster_arn = aws_ecs_cluster.main.arn

    # Fargate Variables
    forge_fargate = true
    fargate_memory = 512
    fargate_cpu = 256
    fargate_iam_role = aws_iam_role.fargate_execution.arn
    ecs_cluster_name = aws_ecs_cluster.main.name
    lambda_container_image_uri = "ghcr.io/podaac/forge:0.11.0-rc.2"
    fargate_max_capacity = 100
}
