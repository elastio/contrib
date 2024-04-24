data "aws_iam_policy_document" "codebuild_trust" {
  statement {
    sid     = "CodeBuildAssumeRole"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["codebuild.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "codepipeline_trust" {
  statement {
    sid     = "CodePipelineAssumeRole"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["codepipeline.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "codebuild_service" {
  statement {
    sid    = "CloudWatchLogsAccess"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    resources = ["*"]
  }

  statement {
    sid       = "DBSecretsManagerActions"
    effect    = "Allow"
    actions   = ["secretsmanager:Get*"]
    resources = [aws_secretsmanager_secret.db.arn]
  }

  statement {
    sid    = "CodePipelineS3BucketAccess"
    effect = "Allow"
    actions = [
      "s3:PutObject",
      "s3:GetObject",
      "s3:GetObjectVersion",
      "s3:GetBucketAcl",
      "s3:GetBucketLocation"
    ]
    resources = [
      "arn:aws:s3:::codepipeline-*"
    ]
  }

  statement {
    sid    = "CodeBuildActions"
    effect = "Allow"
    actions = [
      "codebuild:CreateReportGroup",
      "codebuild:CreateReport",
      "codebuild:UpdateReport",
      "codebuild:BatchPutTestCases",
      "codebuild:BatchPutCodeCoverages"
    ]
    resources = ["*"]
  }

  statement {
    sid    = "EC2Actions"
    effect = "Allow"
    actions = [
      "ec2:Describe*"
    ]
    resources = ["*"]
  }
}

data "aws_iam_policy_document" "codepipeline" {
  statement {
    sid       = "CodePipelinePassRole"
    effect    = "Allow"
    actions   = ["iam:PassRole"]
    resources = ["*"]
    condition {
      test     = "StringEqualsIfExists"
      variable = "iam:PassedToService"
      values = [
        "cloudformation.amazonaws.com",
        "elasticbeanstalk.amazonaws.com",
        "ec2.amazonaws.com",
        "ecs-tasks.amazonaws.com"
      ]
    }
  }

  statement {
    sid       = "CodeCommitActions"
    effect    = "Allow"
    resources = ["*"]
    actions = [
      "codedeploy:CreateDeployment",
      "codedeploy:GetApplication",
      "codedeploy:GetApplicationRevision",
      "codedeploy:GetDeployment",
      "codedeploy:GetDeploymentConfig",
      "codedeploy:RegisterApplicationRevision"
    ]
  }

  statement {
    sid       = "CodeStarConnectionsAccess"
    effect    = "Allow"
    resources = ["*"]
    actions   = ["codestar-connections:UseConnection"]
  }

  statement {
    sid       = "ComputeDatabaseQueueNotificationManagementPolicy"
    effect    = "Allow"
    resources = ["*"]
    actions = [
      "elasticbeanstalk:*",
      "ec2:*",
      "elasticloadbalancing:*",
      "autoscaling:*",
      "cloudwatch:*",
      "s3:*",
      "sns:*",
      "rds:*",
      "sqs:*",
      "ecs:*"
    ]
  }

  statement {
    sid       = "LambdaInvocations"
    effect    = "Allow"
    resources = ["*"]
    actions   = ["lambda:InvokeFunction", "lambda:ListFunctions"]
  }

  statement {
    sid       = "OpsWorksPolicy"
    effect    = "Allow"
    resources = ["*"]
    actions = [
      "opsworks:CreateDeployment",
      "opsworks:DescribeApps",
      "opsworks:DescribeCommands",
      "opsworks:DescribeDeployments",
      "opsworks:DescribeInstances",
      "opsworks:DescribeStacks",
      "opsworks:UpdateApp",
      "opsworks:UpdateStack"
    ]
  }

  statement {
    sid       = "CloudFormationActions"
    effect    = "Allow"
    resources = ["*"]
    actions = [
      "cloudformation:CreateStack",
      "cloudformation:DeleteStack",
      "cloudformation:DescribeStacks",
      "cloudformation:UpdateStack",
      "cloudformation:CreateChangeSet",
      "cloudformation:DeleteChangeSet",
      "cloudformation:DescribeChangeSet",
      "cloudformation:ExecuteChangeSet",
      "cloudformation:SetStackPolicy",
      "cloudformation:ValidateTemplate"
    ]
  }

  statement {
    sid       = "CodeBuildActions"
    effect    = "Allow"
    resources = ["*"]
    actions = [
      "codebuild:BatchGetBuilds",
      "codebuild:StartBuild",
      "codebuild:BatchGetBuildBatches",
      "codebuild:StartBuildBatch"
    ]
  }

  statement {
    sid       = "DeviceFarmActions"
    effect    = "Allow"
    resources = ["*"]
    actions = [
      "devicefarm:ListProjects",
      "devicefarm:ListDevicePools",
      "devicefarm:GetRun",
      "devicefarm:GetUpload",
      "devicefarm:CreateUpload",
      "devicefarm:ScheduleRun"
    ]
  }

  statement {
    sid       = "ServiceCatalogActions"
    effect    = "Allow"
    resources = ["*"]
    actions = [
      "servicecatalog:ListProvisioningArtifacts",
      "servicecatalog:CreateProvisioningArtifact",
      "servicecatalog:DescribeProvisioningArtifact",
      "servicecatalog:DeleteProvisiningArtifact",
      "servicecatalog:UpdateProduct"
    ]
  }

  statement {
    sid       = "ECRActions"
    effect    = "Allow"
    resources = ["*"]
    actions   = ["ecr:DescribeImages"]
  }

  statement {
    sid       = "StatesManagerActions"
    effect    = "Allow"
    resources = ["*"]
    actions = [
      "states:DescribeExecution",
      "states:DescribeStateMachine",
      "states:StartExecution"
    ]
  }

  statement {
    sid       = "AppConfigManagement"
    effect    = "Allow"
    resources = ["*"]
    actions = [
      "appconfig:StartDeployment",
      "appconfig:StopDeployment",
      "appconfig:GetDeployment"
    ]
  }
}

resource "aws_iam_policy" "codebuild_service" {
  for_each = toset(local.codebuild_projects)

  name        = format("CodeBuildBasePolicy-%s-%s", each.value, data.aws_region.current.name)
  path        = "/service-role/"
  description = "Policy used in trust relationship with CodeBuild"
  policy      = data.aws_iam_policy_document.codebuild_service.json
}

resource "aws_iam_role" "codebuild_service" {
  for_each = toset(local.codebuild_projects)

  name               = format("codebuild-%s-service-role", each.value)
  description        = "CodeBuild service role for CodePipeline tasks"
  assume_role_policy = data.aws_iam_policy_document.codebuild_trust.json
  path               = "/service-role/"
}

resource "aws_iam_role_policy_attachment" "service" {
  for_each = toset(local.codebuild_projects)

  role       = aws_iam_role.codebuild_service[each.value].name
  policy_arn = aws_iam_policy.codebuild_service[each.value].arn
}

resource "aws_iam_role_policy_attachment" "service2" {
  for_each = toset(local.codebuild_projects)

  role       = aws_iam_role.codebuild_service[each.value].name
  policy_arn = data.aws_iam_policy.elastio_access.arn
}

resource "aws_iam_policy" "pipeline_service" {
  name        = "codepipeline-service-policy-${var.pipeline_name}"
  path        = "/service-role/"
  description = "Grants required access to CodePipeline"
  policy      = data.aws_iam_policy_document.codepipeline.json
}

resource "aws_iam_role" "pipeline_service" {
  name               = "codepipeline-service-role-${var.pipeline_name}"
  description        = "CodePipeline service role for build and deploy"
  assume_role_policy = data.aws_iam_policy_document.codepipeline_trust.json
  path               = "/service-role/"
}

resource "aws_iam_role_policy_attachment" "pipeline_role" {
  role       = aws_iam_role.pipeline_service.name
  policy_arn = aws_iam_policy.pipeline_service.arn
}
