variable prefix{
  description = "prefix to aws resources"
  type = string
  default = ""
}

variable permissions_boundary_arn {
  description = "Permission boundary arn defined under IAM policy.  It is based on venu and no default is provided"
  type = string
}

variable region{
  description = "aws region"
  type = string
  default = "us-west-2"
}

variable "profile" {
  type    = string
  default = null
}

variable "cma_version" {
  type    = string
  default = "v2.0.4"
}

variable "metadata_aggregator_version" {
  type    = string
  default = "8.0.0"
}

variable "cmr_url" {
  type    = string
  default = "https://cmr.uat.earthdata.nasa.gov/"
}

variable "cmr_custom_host" {
  description = "Custom protocol and host to use for CMR requests (e.g. http://cmr-host.com)"
  type        = string
  default     = null
}

variable "cmr_environment" {
  type = string
  default = "UAT"
}

variable "dmrpp_url" {
  description = "The AWS url for the Docker image repository"
  type        = string
}

variable "stage" {}
variable "app_version" {}
variable "buckets_name" {}
variable "aws_security_group_ids" {}

variable "app_name" {
  default = "hitide-backfill"
}

variable "default_tags" {
  type = map(string)
  default = {}
}

variable "throttle_limit" {
  type = number
  default = 500
}

variable "message_visibility_timeout" {
  type = number
  default = 1200
}

variable "step_retry"{
  type = number
  default = 2
}

variable "db_instance_class"{
  type = string
  default = "db.t3.micro"
}

variable "db_storage_size"{
  type = number
  default = 20
}

variable dmrpp_ecs_cpu{
  type = number
  default = 512
}

variable dmrpp_memory_reservation{
  type = number
  default = 512
}

variable dmrpp_desired_count{
  type = number
  default = 1
}

variable "log_destination_arn" {
  type        = string
  default     = null
  description = "Remote kinesis/destination arn for delivering logs. Requires log_api_gateway_to_cloudwatch set to true."
}

######################################################################
#   ECS related variables
######################################################################

variable "key_name" {
  type        = string
  description = "Name of the key being used to create EC2 instances in the cluster"
}

variable "deploy_to_ngap" {
  type       = bool
  default    = true
}
variable "ecs_cluster_desired_size" {
  description = "The desired maximum number of instances for your ECS autoscaling group"
  type        = number
  default     = 1
}

variable "ecs_cluster_min_size" {
  description = "The minimum number of instances for your ECS cluster"
  type        = number
  default     = 1
}

variable "ecs_cluster_max_size" {
  description = "The maximum number of instances for your ECS cluster"
  type        = number
  default     = 2
}

variable "ecs_efs_config" {
  description = "Config for using EFS with ECS instances"
  type        = object({ mount_target_id = string, mount_point = string })
  default     = null
}

variable "ecs_cluster_instance_docker_volume_size" {
  type        = number
  description = "Size (in GB) of the volume that Docker uses for image and metadata storage"
  default     = 50
}

variable "ecs_cluster_instance_type" {
  type        = string
  description = "EC2 instance type for cluster instances"
  default     = "t3.medium"
}

variable "ecs_docker_storage_driver" {
  description = "Storage driver for ECS tasks"
  type        = string
  default     = "devicemapper"
}

variable "ecs_docker_hub_config" {
  description = "Credentials for integrating ECS with containers hosted on Docker Hu"
  type        = object({ username = string, password = string, email = string })
  default     = null
}

variable "ecs_container_stop_timeout" {
  description = "Time duration to wait from when a task is stopped before its containers are forcefully killed if they do not exit normally on their own"
  type        = string
  default     = "2m"
}

variable "ecs_cluster_scale_in_adjustment_percent" {
  type    = number
  default = -5
}

variable "ecs_cluster_scale_in_threshold_percent" {
  type    = number
  default = 25
}

variable "ecs_cluster_scale_out_adjustment_percent" {
  type    = number
  default = 10
}

variable "ecs_cluster_scale_out_threshold_percent" {
  type    = number
  default = 75
}

variable "ecs_custom_sg_ids" {
  description = "User defined security groups to add to the Core ECS cluster"
  type = list(string)
  default = []
}

variable "buckets" {
  type    = map(object({ name = string, type = string }))
  default = {}
}

variable "system_bucket" {
  description = "system bucket to store task_reaper.sh which will be executed during docker image deployment to ECS"
  type        = string
}

variable "ecs_include_docker_cleanup_cronjob" {
  type        = bool
  default     = true
}

variable "cumulus_node_version" {
  type        = string
}

locals {
  backfill_tool_metadata = try(
    jsondecode(file("${path.module}/backfill_tool_metadata.json")),
    {}
  )
}
