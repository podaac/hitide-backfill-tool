locals {
  lambda_retry_policy = [
    {
      ErrorEquals     = ["Lambda.AWSLambdaException"]
      IntervalSeconds = 10
      BackoffRate     = 2.0
      MaxAttempts     = 5
    },
    {
      ErrorEquals     = ["States.ALL"]
      IntervalSeconds = 5
      BackoffRate     = 2.0
      MaxAttempts     = 5
    }
  ]
}
