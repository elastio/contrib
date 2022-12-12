# Scan AWS backup and send result to Amazon EventBridge

---

## Preconditions
- Terraform
- AWS CLI
- Elastio CLI

## Configure EventBridge and SQS
To configure EventBridge and SQS use Terraform and provided configuration file. It will create EventBridge bus and SQS with name: `elastio-iscan`.

1. Create `Main.tf` file with the content provided below.
2. Run `terraform init`
3. Run `terraform apply`

```
provider "aws" {
  default_tags {
    tags = {
    }
  }
}

locals {
  prefix = elastio-iscan
}

// Get the caller identity's session context to assign the role session name
// tag to created resources
data "aws_caller_identity" "this" {}

data "aws_iam_session_context" "this" {
  arn = data.aws_caller_identity.this.arn
}

resource "aws_cloudwatch_event_bus" "this" {
  name = local.prefix
  tags = {
    "elastio:iscan-event-bus" = "true"
  }
}

// Allows Event Bridge write to SQS. Is used for tests only.
resource "aws_sqs_queue_policy" "allow_event_bridge_write_to_sqs" {
  policy    = data.aws_iam_policy_document.allow_event_bridge_write_to_sqs.json
  queue_url = aws_sqs_queue.this.id
}

data "aws_iam_policy_document" "allow_event_bridge_write_to_sqs" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.this.arn]
  }
}

resource "aws_cloudwatch_event_target" "sqs" {
  rule           = aws_cloudwatch_event_rule.this.name
  arn            = aws_sqs_queue.this.arn
  event_bus_name = aws_cloudwatch_event_bus.this.name
}

resource "aws_cloudwatch_event_rule" "this" {
  name           = local.prefix
  event_pattern  = jsonencode({ source = ["elastio.iscan"] })
  event_bus_name = aws_cloudwatch_event_bus.this.name
}

resource "aws_sqs_queue" "this" {
  name = "${local.prefix}-receiver"
}

output "event_bus_arn" {
  value = aws_cloudwatch_event_bus.this.arn
}

output "event_bus_name" {
  value = aws_cloudwatch_event_bus.this.name
}

output "sqs_queue_url" {
  value = aws_sqs_queue.this.id
}
```

## Scan AWS backup
To scan AWS backup use followig command:

```
elastio aws-backup import --rp-vault [rp-vault] --rp-arn [rp-arn] --iscan --send-event --event-bridge-bus elastio-iscan
```
Where: 
- `rp-vault` is a name of the vault where backup is stored
- `rp-arn` ARN of the backup you would like to scan

## View scan report
To get the report of the iscan go to SQS and open `elastio-iscan-receiver`. Navigate to `Send and receive` messages and press `Poll for messages`.