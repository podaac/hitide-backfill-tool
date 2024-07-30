module "tig" {

  source = "https://github.com/podaac/tig/releases/download/0.12.0%2Bb5b7084/tig-terraform-0.12.0+b5b7084.zip"
  // Lambda variables
  prefix = local.resources_name
  lambda_container_image_uri = "ghcr.io/podaac/tig:0.11.0"
  role = aws_iam_role.iam_execution.arn
  cmr_environment = "OPS"
  subnet_ids = var.subnet_ids
  security_group_ids = var.security_group_ids
  task_logs_retention_in_days = "7"
  config_url = "https://hitide.podaac.earthdatacloud.nasa.gov/dataset-configs"
  palette_url = "https://hitide.podaac.earthdatacloud.nasa.gov/palettes"
  memory_size = 3500
  timeout = 900

  # ECS Variables
  tig_ecs = false
  cluster_arn = aws_ecs_cluster.main.arn

  # Fargate Variables
  tig_fargate = true
  fargate_iam_role = aws_iam_role.fargate_execution.arn
  ecs_cluster_name = aws_ecs_cluster.main.name
  fargate_max_capacity = 100
  fargate_cpu = 2048
  fargate_memory = 16384
  threshold_scale_down = 25
  period_scale_down = 240
}
