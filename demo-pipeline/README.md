# Elastio Demo - CodePipeline
This section of the repository contains Terraform for building a codepipeline to demonstrate the usage of elastio code protection in a theoretical CI/CD pipeline.

## Directory Structure
- `buildspec` - contains buildspec files used by CodeBuild jobs used by the pipeline
- `scripts` - shell scripts used by CodeBuild jobs
- `terraform` - Terraform scripts used to generate a CodePipeline, CodeStar Connection to GitHub, CodeBuild jobs, RDS database, EC2 instance, VPC, and required Roles and Policies


## Deployment
After cloning the repo, change into the `contrib/demo-pipeline/terraform` directory.  Create a `terraform.tfvars` file if you want to change the defaults for the below variables.
`pipeline_name` - Any name just to identify (default: `elastio-demo`)
`region` - The AWS region to deploy to (default: `us-east-2`)
`vpc_cidr_block` - The CIDR block to assign to the demo VPC (default: `10.0.0.0/16`)

```
terraform init
terraform plan
terraform apply
```

## Running the Pipeline
Navigate to CodePipeline in the AWS console and click the Release Change button.  

## When You're Through
Change into the `terraform` directory and run 

```
terraform destroy
```