# Scan AWS backup and send result to Amazon EventBridge

---

## Prerequisites
- Terraform
- AWS CLI
- Elastio CLI

## Configure EventBridge and SQS
Scan report will be sent to the EventBridge bus. For testing purpose SQS queue could be created to poll and view sent events.
To configure EventBridge and SQS use Terraform and provided configuration file. It will create EventBridge bus and SQS queue with name: `elastio-iscan`.

Perform following steps:
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
  prefix = "elastio-iscan"
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
To scan AWS backup use command below. It will import AWS backup to elastio and run vulnerability scan.
```
elastio aws-backup import --rp-vault [rp-vault] --rp-arn [rp-arn] --iscan --send-event --event-bridge-bus elastio-iscan
```
Where: 
- `rp-vault` is a name of the vault where backup is stored
- `rp-arn` ARN of the backup you would like to scan

![image](https://user-images.githubusercontent.com/81738703/207306745-fa4a8708-a4cb-461c-b5a9-e7ae9495b488.png)


## View scan report
To get the report of the iscan go to SQS and open `elastio-iscan-receiver`. Navigate to `Send and receive messages` and press `Poll for messages`.
![image](https://user-images.githubusercontent.com/81738703/207305818-66544b86-b4fb-4007-ad2a-e0c8e932e1bc.png)

## Recover from healthy recovery point
Recovery points contain statuses of scans. There are 2 recovery options:
- Restore entire recovery point using `elastio restore` command 
- Restore individual files from recovery point using `elastio mount` command

### View recovery point statuses in elastio tenant
To view recovery point status complete following actions:
1. In left navigation menu go to `Assets` page
2. Click on asset you would like to inspect

Recovery point scan statuses are displayed as red or green icons on each row of the list:
![image](https://user-images.githubusercontent.com/81738703/207309210-1549e916-f358-4b2b-a34d-f122faa1f11d.png)

### Restore recovery point
There is an option to restore EBS or EC2. To do a restore run one of the following commands:
```
elastio ebs restore --rp [rp-ID]
elastio ec2 restore --rp [rp-ID]
```
There is also an option to restore individual files using `elastio mount` command:
```
sudo -E elastio mount rp --rp [rp-ID]
```

This commands can be found in the restore or mount windows in the elastio tenant. To see this command select `restore` or `mount` option on the recovery point drop down menu.
![image](https://user-images.githubusercontent.com/81738703/207312410-aa03fb22-abd4-4975-ba87-0e9b2319727e.png)
