prefix = "sit-hitide-backfill-tool"
stage = "sit"
db_instance_class = "db.t3.micro"
db_storage_size = 20


# ECS cluster variables
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