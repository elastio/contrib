resource "aws_codebuild_project" "steps" {
  for_each = toset(local.codebuild_projects)

  name           = each.value
  service_role   = aws_iam_role.codebuild_service[each.value].arn
  description    = local.project_properties[each.value]["description"]
  encryption_key = "arn:aws:kms:${var.region}:489999593185:alias/aws/s3"

  source {
    buildspec       = local.project_properties[each.value]["buildspec"]
    git_clone_depth = "1"
    type            = "CODEPIPELINE"
  }

  artifacts {
    name = each.value
    type = "CODEPIPELINE"
  }

  cache {
    type = "NO_CACHE"
  }

  environment {
    compute_type                = "BUILD_GENERAL1_SMALL"
    image                       = "aws/codebuild/standard:5.0"
    image_pull_credentials_type = "CODEBUILD"
    privileged_mode             = true
    type                        = "LINUX_CONTAINER"
  }

  logs_config {
    cloudwatch_logs {
      status = "ENABLED"
    }
  }
}

