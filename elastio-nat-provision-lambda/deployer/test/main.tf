provider "aws" {}

locals {
  version = trimspace(file("${path.module}/../../version"))
}

resource "aws_cloudformation_stack" "elastio_nat_provision_stack" {
  name = "elastio-nat-provision-lambda"
  template_url = join(
    "/",
    [
      "https://elastio-prod-artifacts-us-east-2.s3.us-east-2.amazonaws.com",
      "contrib/elastio-nat-provision-lambda/${local.version}",
      "cloudformation-lambda.yaml"
    ]
  )
  tags = {
    "elastio:resource" = "true"
  }
  capabilities = ["CAPABILITY_NAMED_IAM"]
  parameters = {
    EncryptWithCmk         = "true"
    LambdaTracing          = "true"
    IamResourceNamesPrefix = "Prefix"
    IamResourceNamesSuffix = "Suffix"
  }
}
