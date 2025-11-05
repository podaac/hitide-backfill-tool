resource "aws_security_group" "db" {
  description = "controls access to the database"

  vpc_id = data.aws_vpc.default.id
  name   = "${local.resources_name}-db-sg"
  tags   = local.default_tags
}

resource "aws_security_group_rule" "allow_self_in" {
  type              = "ingress"
  security_group_id = aws_security_group.db.id
  protocol          = "tcp"
  from_port         = 3306
  to_port           = 3306
  self              = true
}

resource "aws_security_group_rule" "allow_all_out" {
  type              = "egress"
  security_group_id = aws_security_group.db.id
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks = [
    "0.0.0.0/0",
  ]
}

resource "aws_db_subnet_group" "default" {
  name       = "${local.resources_name}-subnet"
  subnet_ids = data.aws_subnets.private.ids

  tags = local.default_tags
}

resource "random_password" "db_admin_pass" {
  length  = 16
  special = false
}
resource "random_password" "db_user_pass" {
  length  = 16
  special = false
}


## RDS Database
resource "aws_db_instance" "database" {
  identifier             = "${local.resources_name}-rds"
  allocated_storage      = var.db_storage_size
  storage_type           = "gp2"
  engine                 = "mysql"
  engine_version         = "8.0"
  instance_class         = var.db_instance_class
  db_name                   = "hitidebackfilldb"
  username               = "hitidebackfilldbadmin"
  password               = random_password.db_admin_pass.result
  parameter_group_name   = "default.mysql8.0"
  multi_az               = "true"
  vpc_security_group_ids = [aws_security_group.db.id]
  db_subnet_group_name   = aws_db_subnet_group.default.id
  skip_final_snapshot    = true
  tags                   = local.default_tags
  apply_immediately      = true
  allow_major_version_upgrade = true
}


resource "aws_ssm_parameter" "db_admin" {
  name      = "${local.resources_name}-db-admin"
  type      = "String"
  value     = aws_db_instance.database.username
  tags      = local.default_tags
  overwrite = true
}

resource "aws_ssm_parameter" "db_admin_pass" {
  name      = "${local.resources_name}-db-admin-pass"
  type      = "SecureString"
  value     = aws_db_instance.database.password
  tags      = local.default_tags
  overwrite = true
}

resource "aws_ssm_parameter" "db_user" {
  name      = "${local.resources_name}-db-user"
  type      = "String"
  value     = "hitidebackfilluser"
  tags      = local.default_tags
  overwrite = true
}

resource "aws_ssm_parameter" "db_user_pass" {
  name      = "${local.resources_name}-db-user-pass"
  type      = "SecureString"
  value     = random_password.db_user_pass.result
  tags      = local.default_tags
  overwrite = true
}

resource "aws_ssm_parameter" "db_host" {
  name      = "${local.resources_name}-db-host"
  type      = "String"
  value     = aws_db_instance.database.address
  tags      = local.default_tags
  overwrite = true
}

resource "aws_ssm_parameter" "db_name" {
  name      = "${local.resources_name}-db_name"
  type      = "String"
  value     = aws_db_instance.database.db_name
  tags      = local.default_tags
  overwrite = true
}

resource "aws_ssm_parameter" "db_sg" {
  name      = "${local.resources_name}-db-sg"
  type      = "String"
  value     = aws_security_group.db.id
  tags      = local.default_tags
  overwrite = true
}