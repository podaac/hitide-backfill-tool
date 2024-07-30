resource "aws_s3_bucket" "internal" {
   bucket = "${local.resources_name}-internal"
   acl = "private"
}

resource "aws_s3_bucket" "protected" {
   bucket = "${local.resources_name}-protected"
   acl = "private"
}
