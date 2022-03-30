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
      region           = "us-east-2"
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
      region          = "us-east-2"
      namespace       = "InstanceBackup"

      configuration = {
        ProjectName = "EC2InstanceBackup"
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
      region          = "us-east-2"
      namespace       = "DatabaseBackup"

      configuration = {
        ProjectName = "DatabaseBackup"
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
      region          = "us-east-2"
      namespace       = "BackupWaiter"

      configuration = {
        EnvironmentVariables = jsonencode(local.event_arguments)
        ProjectName          = "WaitForBackup"
      }
    }
  }

  stage {
    name = "Deployment"

    action {
      name             = "AttemptDeployment"
      category         = "Build"
      owner            = "AWS"
      provider         = "CodeBuild"
      version          = 1
      input_artifacts  = ["SourceArtifact"]
      output_artifacts = ["BuildArtifact"]
      run_order        = 1
      region           = "us-east-2"
      namespace        = "Deployment"

      configuration = {
        EnvironmentVariables = jsonencode(local.event_arguments)
        ProjectName          = "StubDeployment"
      }
    }
  }
}
