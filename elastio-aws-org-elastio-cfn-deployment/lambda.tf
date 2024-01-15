module "aws_lambda_function" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "6.5.0"

  function_name = "LambdaDeployElastioCfn"
  handler       = "index.lambda_handler"
  runtime       = "python3.8"
  source_path   = "${path.module}/lambda"

  memory_size            = 128
  timeout                = 60
  maximum_retry_attempts = 10

  attach_policy_json = true
  policy_json        = <<-EOT
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "sts:AssumeRole"
                ],
                "Resource": ["*"]
            }
        ]
    }
  EOT

  create_role                   = true
  attach_cloudwatch_logs_policy = true
}

# CloudWatch Event Rule for detecting account creation by CreateAccountResult
resource "aws_cloudwatch_event_rule" "create_account_result" {
  name        = "create-account-result-rule"
  description = "Trigger for successful CreateAccountResult events"

  event_pattern = jsonencode({
    "source" : ["aws.organizations"],
    "detail-type" : ["AWS Service Event via CloudTrail"],
    "detail" : {
      "eventName" : ["CreateAccountResult"],
      "serviceEventDetails.createAccountStatus.state" : ["SUCCEEDED"]
    }
  })
}

# Permission for the Lambda function to be invoked by CreateAccountResult
resource "aws_lambda_permission" "create_account_result" {
  statement_id  = "AllowExecutionFromCloudWatchCreateAccountResult"
  action        = "lambda:InvokeFunction"
  function_name = module.aws_lambda_function.lambda_function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.create_account_result.arn
}

# CloudWatch Event Target to trigger the Lambda function by CreateAccountResult
resource "aws_cloudwatch_event_target" "create_account_result" {
  rule      = aws_cloudwatch_event_rule.create_account_result.name
  target_id = "InvokeLambdaFunction"
  arn       = module.aws_lambda_function.lambda_function_arn
}

# CloudWatch Event Rule for detecting account creation by CreateManagedAccount
resource "aws_cloudwatch_event_rule" "create_managed_account" {
  name        = "create-managed-account-rule"
  description = "Trigger for successful CreateManagedAccount events"

  event_pattern = jsonencode({
    "source" : ["aws.controltower"],
    "detail-type" : ["AWS Service Event via CloudTrail"],
    "detail" : {
      "eventName" : ["CreateManagedAccount"],
      "serviceEventDetails.createManagedAccountStatus.state" : ["SUCCEEDED"]
    }
  })
}

# Permission for the Lambda function to be invoked by CreateManagedAccount
resource "aws_lambda_permission" "create_managed_account" {
  statement_id  = "AllowExecutionFromCloudWatchCreateManagedAccount"
  action        = "lambda:InvokeFunction"
  function_name = module.aws_lambda_function.lambda_function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.create_managed_account.arn
}

# CloudWatch Event Target to trigger the Lambda function by CreateManagedAccount
resource "aws_cloudwatch_event_target" "create_managed_account" {
  rule      = aws_cloudwatch_event_rule.create_managed_account.name
  target_id = "InvokeLambdaFunction"
  arn       = module.aws_lambda_function.lambda_function_arn
}
