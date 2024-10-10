provider "aws" {}

data "aws_caller_identity" "current" {}

locals {
  account = data.aws_caller_identity.current.account_id
}

resource "aws_iam_role" "deployer" {
  name = "ElastioNatProvisionLambdaDeployer"
  assume_role_policy = jsonencode(
    {
      "Version" : "2012-10-17"
      "Statement" : [
        {
          "Effect" : "Allow",
          "Principal" : {
            "AWS" : "arn:aws:iam::${local.account}:root"
          },
          "Action" : "sts:AssumeRole"
        }
      ]
    }
  )
}

resource "aws_iam_role_policy" "manage_cfn_deployment" {
  name = "ManageCfnDeployment"
  role = aws_iam_role.deployer.id
  policy = jsonencode(
    {
      "Version" : "2012-10-17",
      "Statement" : [
        {
          "Effect" : "Allow",
          "Action" : [
            "cloudformation:CreateStack",
            "cloudformation:DeleteStack",
            "cloudformation:UpdateStack",
            "cloudformation:CancelUpdateStack",
            "cloudformation:RollbackStack",
            "cloudformation:ContinueUpdateRollback",
            "cloudformation:DescribeStacks",
            "cloudformation:GetTemplate",

            "iam:CreateRole",
            "iam:DeleteRole",
            "iam:UpdateRole",
            "iam:UpdateRoleDescription",
            "iam:GetRole",

            "iam:TagRole",
            "iam:UntagRole",
            "iam:ListRoleTags",

            "iam:UpdateAssumeRolePolicy",

            "iam:AttachRolePolicy",
            "iam:DetachRolePolicy",
            "iam:ListAttachedRolePolicies",

            "iam:PutRolePolicy",
            "iam:DeleteRolePolicy",
            "iam:GetRolePolicy",
            "iam:ListRolePolicies",

            "iam:PutRolePermissionsBoundary",
            "iam:DeleteRolePermissionsBoundary",

            "logs:CreateLogGroup",
            "logs:DescribeLogGroups",
            "logs:DeleteLogGroup",

            "logs:ListTagsLogGroup",
            "logs:UntagLogGroup",
            "logs:TagLogGroup",
            "logs:TagResource",
            "logs:UntagResource",
            "logs:PutRetentionPolicy",
            "logs:DeleteRetentionPolicy",

            "kms:CreateAlias",
            "kms:DeleteAlias",
            "kms:UpdateAlias",
            "kms:ListAliases",

            # Required when creating a lambda function with encrypted env vars
            "kms:Encrypt",
            "kms:Decrypt",
            "kms:CreateGrant",

            "kms:CreateKey",
            "kms:DescribeKey",
            "kms:UpdateKeyDescription",
            "kms:ScheduleKeyDeletion",

            "kms:EnableKey",
            "kms:DisableKey",

            "kms:EnableKeyRotation",
            "kms:DisableKeyRotation",
            "kms:GetKeyRotationStatus",
            "kms:ListKeyRotations",

            "kms:PutKeyPolicy",
            "kms:GetKeyPolicy",
            "kms:ListKeyPolicies",

            "kms:CancelKeyDeletion",

            "kms:ListResourceTags",
            "kms:TagResource",
            "kms:UntagResource",

            "lambda:CreateFunction",
            "lambda:DeleteFunction",
            "lambda:DeleteFunctionEventInvokeConfig",
            "lambda:PutFunctionEventInvokeConfig",
            "lambda:UpdateFunctionCode",
            "lambda:UpdateFunctionConfiguration",
            "lambda:ListVersionsByFunction",
            "lambda:GetFunction",
            "lambda:GetFunctionConfiguration",
            "lambda:GetFunctionCodeSigningConfig",
            "lambda:GetFunctionEventInvokeConfig",
            "lambda:GetPolicy",

            "lambda:GetEventSourceMapping",
            "lambda:UpdateEventSourceMapping",
            "lambda:CreateEventSourceMapping",
            "lambda:DeleteEventSourceMapping",

            "lambda:AddPermission",
            "lambda:RemovePermission",

            "lambda:ListTags",
            "lambda:TagResource",
            "lambda:UntagResource",

            "states:CreateStateMachine",
            "states:DeleteStateMachine",
            "states:UpdateStateMachine",
            "states:DescribeStateMachine",
            "states:ListStateMachineVersions",

            "states:ListTagsForResource",
            "states:TagResource",
            "states:UntagResource",

            "events:PutTargets",
            "events:RemoveTargets",
            "events:ListTargetsByRule",

            "events:PutRule",
            "events:DeleteRule",
            "events:DescribeRule",

            "events:DisableRule",
            "events:EnableRule",

            "events:TagResource",
            "events:UntagResource",
            "events:ListTagsForResource",

            "scheduler:CreateSchedule",
            "scheduler:GetSchedule",
            "scheduler:UpdateSchedule",
            "scheduler:DeleteSchedule",

            "scheduler:ListTagsForResource",
            "scheduler:TagResource",
            "scheduler:UntagResource",
          ],
          "Resource" : "*"
        },

        {
          "Effect" : "Allow"
          "Action" : [
            "iam:PassRole"
          ],
          "Resource" : "arn:aws:iam::${local.account}:role/*Elastio*"
        },

        # Get access for reading the artifacts (e.g. lambda zip) from the public elastio bucket
        {
          "Effect" : "Allow"
          "Action" : [
            "s3:GetObject"
          ],
          "Resource" : "arn:aws:s3:::elastio*"
        }
      ]
    }
  )
}
