module backfill_lambdas{

  source = "https://github.com/podaac/hitide-backfill-lambdas/releases/download/0.1.0%2B0993027/hitide-backfill-lambdas-0.1.0+0993027.zip"
  lambda_role = aws_iam_role.iam_execution.arn
  layers = [aws_lambda_layer_version.cumulus_message_adapter.arn]
  prefix = local.resources_name
  forge_step_arn = aws_sfn_state_machine.forge.arn
  tig_step_arn = aws_sfn_state_machine.tig.arn
  dmrpp_step_arn = aws_sfn_state_machine.dmrpp.arn
  sqs_url = aws_sqs_queue.sqs-queue.url
  region = var.region
  aws_profile = var.profile
  subnet_ids = data.aws_subnets.private.ids
  security_group_ids = concat(var.security_group_ids,[aws_security_group.db.id])
  step_retry = var.step_retry
  message_visibility_timeout = var.message_visibility_timeout
  reserved_concurrent_executions = 1
  timeout = 900

  #db variables
  user_name = aws_ssm_parameter.db_user.name
  user_pass = aws_ssm_parameter.db_user_pass.name
  root_user = aws_ssm_parameter.db_admin.name
  root_pass = aws_ssm_parameter.db_admin_pass.name
  db_host = aws_ssm_parameter.db_host.name
  db_name = aws_ssm_parameter.db_name.name

  ssm_throttle_limit = aws_ssm_parameter.throttle_limit.name
}

resource "aws_cloudwatch_event_rule" "every_one_minutes" {
    name = "${local.resources_name}-every-one-minutes"
    description = "Fires every one minutes"
    schedule_expression = "cron(* * * * ? *)"
}

resource "aws_cloudwatch_event_target" "backfill_sqs_to_step_every_five_minutes" {
    rule = aws_cloudwatch_event_rule.every_one_minutes.name
    arn = module.backfill_lambdas.backfill_sqs_to_step_task_arn
}

resource "aws_lambda_permission" "allow_cloudwatch_to_call_backfill_sqs_to_step" {
    statement_id = "AllowExecutionFromCloudWatch"
    action = "lambda:InvokeFunction"
    function_name = module.backfill_lambdas.backfill_sqs_to_step_function_name
    principal = "events.amazonaws.com"
    source_arn = aws_cloudwatch_event_rule.every_one_minutes.arn
}

resource "aws_ssm_parameter" "throttle_limit" {
  name      = "${local.resources_name}-throttle-limit"
  type      = "String"
  value     = var.throttle_limit
  tags      = local.default_tags
  overwrite = true
}
