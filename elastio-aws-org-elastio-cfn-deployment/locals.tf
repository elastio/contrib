locals {
  aws_region = data.aws_region.this.name

  cfn_template_initial_version = "https://cloudformation-templates20210930070513386900000003.s3.us-east-2.amazonaws.com/axksy1mLJmcEIq9a5qsb.json"
  cfn_templates = {
    "elastio_cfn_v2" = {
      name         = "Version 2"
      description  = "Version 2"
      template_url = "https://cloudformation-templates20210930070513386900000003.s3.us-east-2.amazonaws.com/ZVoajmeIxetbXq1Hl5I1.json"
    }
  }
}
