# ===== main.tf =====

locals {
  tags = {
    "example-custom-tag" : "foo",
    "elastio:resource" : "true",
    "elastio:stack" : "asset-account",
  }
  account_id = data.aws_caller_identity.current.account_id
}

data "aws_caller_identity" "current" {}

resource "aws_iam_role" "inventory_event_target" {
  name                 = "ElastioInventoryEventTarget"
  tags                 = local.tags
  description          = "Role assumed by EventBridge to send events to the Elastio Connector"
  permissions_boundary = "arn:aws:iam::aws:policy/AdministratorAccess"
  assume_role_policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Principal" : { "Service" : "events.amazonaws.com" },
        "Action" : "sts:AssumeRole",
      },
    ],
  })
}

resource "aws_iam_role_policy" "inventory_event_target" {
  role   = aws_iam_role.inventory_event_target.name
  name   = each.key
  policy = jsonencode({ "Version" : "2012-10-17", "Statement" : each.value })
  for_each = {
    "SendEventsToConnectorAccount" : [
      {
        "Effect" : "Allow",
        "Resource" : "arn:aws:events:*:123456789012:event-bus/elastio-*",
        "Action" : [
          // Send inventory events to the Connector about
          // new EC2 instances or AWS Backup recovery points
          "events:PutEvents",
        ],
      },
    ],
  }
}

resource "aws_iam_role" "asset_region_stack_deployer" {
  name                 = "ElastioAssetRegionStackDeployer"
  tags                 = local.tags
  description          = "Used by CloudFormation to deploy region-level stack"
  permissions_boundary = "arn:aws:iam::aws:policy/AdministratorAccess"
  assume_role_policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Principal" : { "Service" : "cloudformation.amazonaws.com" },
        "Action" : [
          // This role is assumed directly by CloudFormation to deploy
          // the region-level stacks with EventBridge subscriptions
          "sts:AssumeRole",
        ],
      },
    ],
  })
}

resource "aws_iam_role_policy" "asset_region_stack_deployer" {
  role   = aws_iam_role.asset_region_stack_deployer.name
  name   = each.key
  policy = jsonencode({ "Version" : "2012-10-17", "Statement" : each.value })
  for_each = {
    "ManageElastioEventBridgeRules" : [
      {
        "Effect" : "Allow",
        "Resource" : "arn:aws:events:*:${local.account_id}:rule/elastio-*",
        "Action" : [
          // Allow CFN to manage EventBridge subscriptions that get events about
          // new EC2 instances or AWS Backup recovery points
          "events:DescribeRule",
          "events:ListTargetsByRule",
          "events:ListTagsForResource",
          "events:PutRule",
          "events:PutTargets",
          "events:RemoveTargets",
          "events:DeleteRule",
          "events:EnableRule",
          "events:DisableRule",
        ],
      },

      {
        "Effect" : "Allow",
        "Resource" : "${aws_iam_role.inventory_event_target.arn}",
        "Action" : [
          // Allow CFN to manage the assignment of the InventoryEventTarget role
          "iam:PassRole",
        ],
      },
    ],
  }
}

resource "aws_iam_role" "cloud_connector" {
  name                 = "ElastioCloudConnector"
  tags                 = local.tags
  description          = "Allows Elastio Cloud Connector to access the assets in this account"
  permissions_boundary = "arn:aws:iam::aws:policy/AdministratorAccess"
  assume_role_policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Principal" : {
          "AWS" : "arn:aws:iam::123456789012:role/ElastioCloudConnectorBastion",
        },
        "Condition" : { "StringEquals" : { "sts:ExternalId" : "$external_id" } },
        "Action" : [
          // Elastio Connector acts on behalf of this role in the protected account
          "sts:AssumeRole",
        ],
      },
    ],
  })
}

resource "aws_iam_role_policy" "cloud_connector" {
  role   = aws_iam_role.cloud_connector.name
  name   = each.key
  policy = jsonencode({ "Version" : "2012-10-17", "Statement" : each.value })
  for_each = {
    "Backup" : [
      {
        "Effect" : "Allow",
        "Resource" : "*",
        "Action" : [
          // AWS Backup inventory
          "backup:ListTags",
          "backup:ListProtectedResources",
          "backup:ListProtectedResourcesByBackupVault",
          "backup:ListBackupVaults",
          "backup:DescribeBackupVault",
          "backup:ListRecoveryPointsByResource",
          "backup:DescribeRecoveryPoint",
          "backup:ListRecoveryPointsByBackupVault",
          "backup:GetRecoveryPointRestoreMetadata",
        ],
      },
    ],
    "EFS" : [
      {
        "Effect" : "Allow",
        "Resource" : "*",
        "Action" : [
          // EFS inventory
          "elasticfilesystem:DescribeFileSystems",
          "elasticfilesystem:ListTagsForResource",
          "elasticfilesystem:DescribeTags",
        ],
      },
    ],
    "FSx" : [
      {
        "Effect" : "Allow",
        "Resource" : "*",
        "Action" : [
          // FSx inventory
          "fsx:DescribeVolumes",
          "fsx:DescribeBackups",
          "fsx:DescribeFileSystems",
          "fsx:DescribeStorageVirtualMachines",
          "fsx:ListTagsForResource",
        ],
      },
    ],
    "EC2" : [
      {
        "Effect" : "Allow",
        "Resource" : "*",
        "Action" : [
          // EC2 inventory
          "ec2:DescribeTags",
          "ec2:DescribeInstances",
          "ec2:DescribeImages",
          "ec2:DescribeHosts",
          "ec2:DescribeVolumes",
          "ec2:DescribeVolumeStatus",
          "ec2:DescribeSnapshots",
          "ec2:DescribeSnapshotAttribute",

          // EBS snapshot sizes estimation
          "ebs:ListSnapshotBlocks",
          "ebs:ListChangedBlocks",
        ],
      },

      {
        "Effect" : "Allow",
        "Resource" : "*",
        "Action" : [
          // Required if only direct EBS snapshot scan is possible
          "ebs:GetSnapshotBlock",

          // Required in case if the snapshot can't be directly shared
          // (e.g. it uses an AWS managed key for encryption)
          "ec2:CopySnapshot",

          // Create snapshots from the live EC2/EBS to scan them directly
          "ec2:CreateSnapshot",
          "ec2:CreateSnapshots",
        ],
      },

      {
        "Effect" : "Allow",
        "Resource" : ["arn:aws:ec2:*:*:volume/*", "arn:aws:ec2:*::snapshot/*"],
        "Condition" : { "StringLike" : { "ec2:CreateAction" : "*" } },
        "Action" : [
          // Allow assigning tags when creating new resources
          "ec2:CreateTags",
        ],
      },

      {
        "Effect" : "Allow",
        "Resource" : "*",
        "Condition" : {
          "StringLike" : { "aws:ResourceTag/elastio:resource" : "*" },
        },
        "Action" : [
          // Delete/update temporary Elastio-managed snapshots
          "ec2:DeleteSnapshot",
          "ec2:CreateTags",
          "ec2:DeleteTags",

          // Terminate temporary EC2 instances in AWS Backup restore test scenario
          "ec2:StopInstances",
          "ec2:TerminateInstances",
        ],
      },

      {
        "Effect" : "Allow",
        "Resource" : "*",
        "Condition" : { "StringEquals" : { "ec2:Add/userId" : "123456789012" } },
        "Action" : [
          // Share snapshots with the Connector account if possible
          // to avoid unnecessary copying
          "ec2:ModifySnapshotAttribute",
        ],
      },

      {
        "Effect" : "Allow",
        "Resource" : "*",
        "Condition" : {
          "StringLike" : { "aws:ResourceTag/awsbackup-restore-test" : "*" },
        },
        "Action" : [
          // Access the temporary EC2 instance created as part of
          // the AWS Backup restore testing scenario
          "ec2:ModifyInstanceAttribute",
          "ec2:CreateTags",
          "ec2:DeleteTags",
        ],
      },
    ],
    "SSM" : [
      {
        "Effect" : "Allow",
        "Resource" : [
          "arn:aws:ssm:*:${local.account_id}:parameter/elastio/*",
          "arn:aws:ssm:*::parameter/aws/*",
        ],
        "Action" : [
          // Read SSM parameter configurations
          "ssm:GetParameters",
          "ssm:GetParameter",
        ],
      },

      {
        "Effect" : "Allow",
        "Resource" : [
          "arn:aws:ssm:*:*:document/AWSEC2-CreateVssSnapshot",
          "arn:aws:ec2:*:*:instance/*",
        ],
        "Action" : [
          // Create the VSS snapshot
          "ssm:SendCommand",
        ],
      },

      {
        "Effect" : "Allow",
        "Resource" : "*",
        "Action" : [
          // Track the VSS snapshot creation command execution
          "ssm:GetConnectionStatus",
          "ssm:GetCommandInvocation",
          "ssm:ListCommands",
        ],
      },

      {
        "Effect" : "Allow",
        "Resource" : "*",
        "Action" : [
          // EC2 inventory
          "ssm:DescribeInstanceInformation",
        ],
      },
    ],
    "IAM" : [
      {
        "Effect" : "Allow",
        "Resource" : "*",
        "Action" : [
          // Preliminary checks for permissions to do an app-consistent
          // snapshot for an EC2 instance
          "iam:GetInstanceProfile",
          "iam:SimulatePrincipalPolicy",
        ],
      },
    ],
    "DRS" : [
      {
        "Effect" : "Allow",
        "Resource" : "*",
        "Action" : [
          // DRS inventory
          "drs:DescribeRecoverySnapshots",
          "drs:DescribeSourceServers",
          "drs:ListTagsForResource",
        ],
      },
    ],
    "S3" : [
      {
        "Effect" : "Allow",
        "Resource" : "*",
        "Action" : [
          // S3 inventory
          "s3:ListAllMyBuckets",
          "s3:GetBucketLocation",
          "s3:GetBucketObjectLockConfiguration",
          "s3:GetBucketAcl",
          "s3:GetBucketVersioning",
          "s3:GetBucketPolicy",
          "s3:GetBucketLogging",
          "s3:GetReplicationConfiguration",
          "s3:GetMetricsConfiguration",
          "s3:GetLifecycleConfiguration",
          "s3:GetInventoryConfiguration",
          "s3:GetIntelligentTieringConfiguration",
          "s3:GetEncryptionConfiguration",
          "s3:GetBucketWebsite",
          "s3:GetBucketRequestPayment",
          "s3:GetBucketPublicAccessBlock",
          "s3:GetBucketOwnershipControls",
          "s3:GetBucketNotification",
          "s3:GetAnalyticsConfiguration",
          "s3:GetAccelerateConfiguration",

          // S3 scanning
          "s3:ListBucket",
          "s3:GetObjectVersion",
          "s3:GetObject",
          "s3:GetBucketTagging",
        ],
      },
    ],
    "SQS" : [
      {
        "Effect" : "Allow",
        "Resource" : "*",
        "Condition" : {
          "StringLike" : { "aws:ResourceTag/elastio:resource" : "*" },
        },
        "Action" : [
          // Read SQS queues with S3 changelog for incremental S3 scanning
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
        ],
      },
    ],
    "KMS" : [
      {
        "Effect" : "Allow",
        "Resource" : "*",
        "Action" : [
          // KMS inventory
          "kms:DescribeKey",
        ],
      },

      {
        "Effect" : "Allow",
        "Resource" : "*",
        "Condition" : {
          "StringLike" : {
            "aws:ResourceTag/elastio:authorize" : "*",
            "aws:ResourceTag/elastio:resource" : "*",
          },
        },
        "Action" : [
          // Access data protected by KMS encryption
          "kms:ReEncryptFrom",
          "kms:ReEncryptTo",
          "kms:CreateGrant",
          "kms:Encrypt",
          "kms:GenerateDataKey",
          "kms:GenerateDataKeyWithoutPlaintext",
          "kms:Decrypt",
        ],
      },
    ],
    "Account" : [
      {
        "Effect" : "Allow",
        "Resource" : "*",
        "Action" : [
          // AWS Account geometry inventory
          "iam:ListAccountAliases",
          "ec2:DescribeRegions",
        ],
      },
    ],
    "VPC" : [
      {
        "Effect" : "Allow",
        "Resource" : "*",
        "Action" : [
          // VPC inventory
          "ec2:DescribeVpcs",
          "ec2:DescribeSubnets",
          "ec2:DescribeAvailabilityZones",
          "ec2:DescribeRouteTables",
          "ec2:DescribeNatGateways",
          "ec2:DescribeSecurityGroups",
          "ec2:DescribeVpcEndpoints",
        ],
      },
    ],
    "CloudFormation" : [
      {
        "Effect" : "Allow",
        "Resource" : "*",
        "Action" : [
          // CloudFormation inventory
          "cloudformation:DescribeStacks",
          "cloudformation:DescribeStackSet",
          "cloudformation:ListStacks",
        ],
      },

      {
        "Effect" : "Allow",
        "Resource" : "arn:aws:cloudformation:*:${local.account_id}:stack/elastio-*/*",
        "Condition" : {
          "StringEquals" : {
            "cloudformation:RoleArn" : "${aws_iam_role.asset_region_stack_deployer.arn}",
          },
        },
        "Action" : [
          // Elastio regional CloudFormation stack management (creates, updates)
          "cloudformation:CreateStack",
          "cloudformation:UpdateStack",
        ],
      },

      {
        "Effect" : "Allow",
        "Resource" : "${aws_iam_role.asset_region_stack_deployer.arn}",
        "Action" : [
          // Allows running cloudformation:CreateStack/UpdateStack
          // on behalf of the deployer role.
          "iam:PassRole",
        ],
      },

      {
        "Effect" : "Allow",
        "Resource" : "arn:aws:cloudformation:*:${local.account_id}:stack/elastio-*/*",
        "Condition" : { "StringLike" : { "cloudformation:CreateAction" : "*" } },
        "Action" : [
          // Elastio CloudFormation stacks management (tagging on create)
          "cloudformation:TagResource",
        ],
      },

      {
        "Effect" : "Allow",
        "Resource" : "arn:aws:cloudformation:*:${local.account_id}:stack/elastio-*/*",
        "Condition" : {
          "StringLike" : { "aws:ResourceTag/elastio:resource" : "*" },
        },
        "Action" : [
          // Elastio CloudFormation stacks management (updates, deletes)
          "cloudformation:DeleteStack",
          "cloudformation:TagResource",
          "cloudformation:UntagResource",
        ],
      },
    ],
  }
}

resource "aws_ssm_parameter" "stack_meta" {
  name        = "/elastio/asset/account/stack-meta"
  description = "Asset Account stack metadata discovered and read by the Connector"
  value = jsonencode({
    "version" : "$VERSION",
    "terraform" : {},
    "inventory_event_target_role_arn" : "${aws_iam_role.inventory_event_target.arn}",
    "asset_region_stack_deployer_role_arn" : "${aws_iam_role.asset_region_stack_deployer.arn}",
    "cloud_connector_role_arn" : "${aws_iam_role.cloud_connector.arn}",
    "capabilities" : {
      "ec2" : { "scan" : true },
      "drs" : {},
      "s3" : { "scan" : true },
      "efs" : {},
      "fsx" : {},
      "backup" : {},
    },
    "tags" : { "example-custom-tag" : "foo" },
  })
  type = "String"
  tags = merge(local.tags, { "elastio:parameter" : "stack-meta" })
}
