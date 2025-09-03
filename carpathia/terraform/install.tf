locals {
  system_bucket = coalesce(
    var.system_bucket,
    "${local.system_prefix}-ec2"
  )
}

data "aws_s3_bucket" "system" {
  bucket = local.system_bucket
}

resource "aws_s3_object" "ansible" {
  for_each = fileset("${path.module}/../ansible", "**")

  bucket = data.aws_s3_bucket.system.bucket
  key = "bootstrap/${local.name}/ansible/${each.value}"
  source = "${path.module}/../ansible/${each.value}"
  source_hash = filemd5("${path.module}/../ansible/${each.value}")
}
