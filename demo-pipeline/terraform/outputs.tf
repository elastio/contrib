output "codepipeline_id" {
  value = aws_codepipeline.pipe.id
}

output "codebuild_projects" {
  value = { for i in local.codebuild_projects.* : i => aws_codebuild_project.steps[i].id }
}

output "instance_id" {
  value = aws_instance.test_instance.id
}

output "instance_public_ip" {
  value = aws_instance.test_instance.public_ip
}

output "instance_profile" {
  value = aws_iam_instance_profile.elastio_instance
}

output "database_endpoint" {
  value = aws_db_instance.test_instance.endpoint
}

output "codpepipeline_artifact_bucket" {
  value = aws_s3_bucket.codepipeline_bucket.bucket
}

output "codepipeline_service_role" {
  value = aws_iam_role.pipeline_service.arn
}

output "codebuild_service_roles" {
  value = { for i in local.codebuild_projects.* : i => aws_iam_role.codebuild_service[i].arn }
}

output "codebuild_policies" {
  value = { for i in local.codebuild_projects.* : i => aws_iam_policy.codebuild_service[i].arn }
}

output "codepipeline_policy" {
  value = aws_iam_policy.pipeline_service.arn
}
