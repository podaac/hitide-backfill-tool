locals {
  tags = {
    Deployment = var.prefix
  }
}

terraform {
  required_providers {
    aws  = "~> 5.0"
    null = "~> 2.1"
  }
}

provider "aws" {
  region  = var.region
  profile = var.profile
  shared_credentials_files = [var.credentials]

  ignore_tags {
    key_prefixes = ["gsfc-ngap"]
  }
}

locals {
  name = var.app_name
  environment = var.stage

  # This is the convention we use to know what belongs to each other
  resources_name = terraform.workspace == "default" ? "podaac-services-${local.environment}-${local.name}" : "podaac-services-${local.environment}-${local.name}-${terraform.workspace}"

  # Account ID used for getting the ECR host
  account_id = data.aws_caller_identity.current.account_id

  default_tags = length(var.default_tags) == 0 ? {
    team: "TVA",
    application: local.resources_name,
    Environment = var.stage
    Version = var.app_version
  } : var.default_tags

  buckets = {
    protected = {
      name = var.buckets_name
      type = "protected"
    }
  }

}