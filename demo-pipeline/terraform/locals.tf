locals {
  project_properties = {
    EC2InstanceBackup : {
      buildspec : "demo-pipeline/buildspec/instance-backup.yaml"
      description : "Run a backup of an EC2 Instance"
    },
    MockDeployment : {
      buildspec : "demo-pipeline/buildspec/deployment.yaml"
      description : "Run an intentionall failed deployment and demonstrate in-pipeline recovery"
    },
    DatabaseBackup : {
      buildspec : "demo-pipeline/buildspec/database-backup.yaml"
      description : "Perform a backup of our application's Postgres database"
    },
    WaitForBackup : {
      buildspec : "demo-pipeline/buildspec/wait-for-backup.yaml"
      description : "Waits for a backup to complete"
    }
  }
  codebuild_projects = keys(local.project_properties)
}
