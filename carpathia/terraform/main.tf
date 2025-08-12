terraform {
  required_version = ">=1.2.7"

  backend "s3" {
    key = "services/hitide-backfill-tool-carpathia/terraform.tfstate"
  }

  required_providers {
    aws = {
      source = "hashicorp/aws"
      version = ">=5.20.0"
    }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = local.default_tags
  }

  ignore_tags {
    key_prefixes = ["gsfc-ngap"]
  }
}

data "local_file" "pyproject_toml" {
  filename = abspath("${path.root}/../../pyproject.toml")
}

locals {
  name        = regex("name = \"(\\S*)\"", data.local_file.pyproject_toml.content)[0]
  version     = regex("version = \"(\\S*)\"", data.local_file.pyproject_toml.content)[0]
  environment = var.stage

  resource_prefix = "${local.name}-${local.environment}"
  system_prefix = coalesce(
    var.system_prefix,
     "${var.cumulus_prefix}-carpathia"
  )

  default_tags = length(var.default_tags) == 0 ? {
    team = "TVA"
    application = local.resource_prefix
    version = local.version
    Environment = local.environment
  } : var.default_tags
}