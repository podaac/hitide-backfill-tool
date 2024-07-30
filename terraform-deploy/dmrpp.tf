module "dmrpp-generator" {

  // Required parameters
  source = "https://github.com/ghrcdaac/dmrpp-generator/releases/download/v5.0.1/dmrpp-generator.zip"
  cluster_arn = aws_ecs_cluster.default.arn
  log_destination_arn = var.log_destination_arn
  region = var.region
  prefix = var.prefix
  docker_image = var.dmrpp_generator_docker_image
  // Optional parameters
  cpu = var.dmrpp_ecs_cpu // default to 512
  memory_reservation = var.dmrpp_memory_reservation // default to 512Mb
  desired_count = var.dmrpp_desired_count  // Default to 1
  get_dmrpp_timeout = 600 // Set dmrpp process timeout to 10 minute

  // Optional Lambda Specific Configuration  
  cumulus_lambda_role_arn = aws_iam_role.iam_execution.arn // If provided the lambda will be provisioned
  timeout = 900
  memory_size = 256
  ephemeral_storage = 4096
  
 }
 