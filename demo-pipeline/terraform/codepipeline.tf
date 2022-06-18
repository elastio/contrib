locals {
  event_arguments = [
    {
      name  = "INSTANCE_RP_ID"
      value = "#{InstanceBackup.INSTANCE_RP_ID}"
      type  = "PLAINTEXT"
    },
    {
      name  = "DB_RP_ID"
      value = "#{DatabaseBackup.DB_RESTORE_POINT}"
      type  = "PLAINTEXT"
    }
  ]
}

resource "aws_codestarconnections_connection" "github" {
  name          = "GitHubV2Connection"
  provider_type = "GitHub"
}

resource "aws_s3_bucket" "codepipeline_bucket" {
  bucket_prefix = "codepipeline-${var.region}-"
}

resource "aws_codepipeline" "pipe" {
  name     = "elastio-test-pipeline"
  role_arn = aws_iam_role.pipeline_service.arn

  artifact_store {
    location = aws_s3_bucket.codepipeline_bucket.bucket
    type     = "S3"
  }

  stage {
    name = "Source"

    action {
      name             = "Source"
      category         = "Source"
      owner            = "AWS"
      provider         = "CodeStarSourceConnection"
      version          = 1
      output_artifacts = ["SourceArtifact"]
      run_order        = 1
      region           = var.region
      namespace        = "SourceVariables"

      configuration = {
        ConnectionArn        = aws_codestarconnections_connection.github.arn
        FullRepositoryId     = "elastio/contrib"
        BranchName           = "gwojtak/pipeline-demo"
        DetectChanges        = "true"
        OutputArtifactFormat = "CODE_ZIP"
      }
    }
  }

  stage {
    name = "ResourceProtection"

    action {
      name            = "EC2InstanceBackup"
      category        = "Build"
      owner           = "AWS"
      provider        = "CodeBuild"
      version         = 1
      input_artifacts = ["SourceArtifact"]
      run_order       = 1
      region          = var.region
      namespace       = "InstanceBackup"

      configuration = {
        ProjectName = "EC2InstanceBackup"
        EnvironmentVariables = jsonencode(
          [{
            name  = "ENVIRONMENT"
            type  = "PLAINTEXT"
            value = "demo"
        }])
      }
    }

    action {
      name            = "Pre-MigrationDBDump"
      category        = "Build"
      owner           = "AWS"
      provider        = "CodeBuild"
      version         = 1
      input_artifacts = ["SourceArtifact"]
      run_order       = 1
      region          = var.region
      namespace       = "DatabaseBackup"

      configuration = {
        ProjectName = "DatabaseBackup"
        EnvironmentVariables = jsonencode(
          [{
            name  = "ENVIRONMENT"
            type  = "PLAINTEXT"
            value = "demo"
        }])
      }
    }
  }

  stage {
    name = "StandBy"

    action {
      name            = "WaitForInstanceBackup"
      category        = "Build"
      owner           = "AWS"
      provider        = "CodeBuild"
      version         = 1
      input_artifacts = ["SourceArtifact"]
      run_order       = 1
      region          = var.region
      namespace       = "BackupWaiter"

      configuration = {
        EnvironmentVariables = jsonencode([{
          name  = "JOB_ID"
          type  = "PLAINTEXT"
          value = "#{InstanceBackup.JOB_ID}"
          },
          {
            name  = "ABORT_TOKEN"
            type  = "PLAINTEXT"
            value = "#{InstanceBackup.ABORT_TOKEN}"
        }])
        ProjectName = "WaitForBackup"
      }
    }
  }

  stage {
    name = "Deployment"

    action {
      name             = "MockDeployment"
      category         = "Build"
      owner            = "AWS"
      provider         = "CodeBuild"
      version          = 1
      input_artifacts  = ["SourceArtifact"]
      output_artifacts = ["BuildArtifact"]
      run_order        = 1
      region           = var.region
      namespace        = "Deployment"

      configuration = {
        EnvironmentVariables = jsonencode(local.event_arguments)
        ProjectName          = "MockDeployment"
      }
    }
  }
}
