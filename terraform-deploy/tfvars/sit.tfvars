prefix = "sit-hitide-backfill-tool"
permissions_boundary_arn = var.permissions_boundary_arn
stage = "sit"
db_instance_class = "db.t2.micro"
db_storage_size = 20


# ECS cluster variables
# Bucket name
buckets = {
  protected = {
    name = var.buckets_name
    type = "protected"
  }
} 
system_bucket = var.system_bucket
key_name = "backfill-tool-sit-cluster-keypair"
ecs_container_stop_timeout = "45m"
ecs_cluster_desired_size = 1
ecs_cluster_min_size = 1
ecs_cluster_max_size =2
ecs_include_docker_cleanup_cronjob = true

dmrpp_desired_count = 8
dmrpp_ecs_cpu = 64
dmrpp_memory_reservation = 256
ecs_cluster_instance_docker_volume_size = 100