prefix = "uat-hitide-backfill-tool"
permissions_boundary_arn = var.permissions_boundary_arn
stage = "uat"
db_instance_class = "db.t3.large"
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
key_name = "backfill-tool-uat-cluster-keypair"
ecs_container_stop_timeout = "45m"

ecs_include_docker_cleanup_cronjob = true
throttle_limit = 500

# Many DMRPP EC2 Strategy

ecs_cluster_desired_size = 4
ecs_cluster_min_size = 4
ecs_cluster_max_size = 5
dmrpp_desired_count = 5
dmrpp_ecs_cpu = 1800
dmrpp_memory_reservation = 900
ecs_cluster_instance_type = "t3a.medium"
ecs_cluster_instance_docker_volume_size = 50

#ecs_cluster_desired_size = 1
#ecs_cluster_min_size = 1
#ecs_cluster_max_size =2
#dmrpp_desired_count = 50
#dmrpp_ecs_cpu = 64
#dmrpp_memory_reservation = 256
#ecs_cluster_instance_type = "t3.xlarge"
#ecs_cluster_instance_docker_volume_size = 600

message_visibility_timeout = 7200
