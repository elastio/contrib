resource "aws_cloudformation_stack_set" "elastio_cfn_role" {
  name             = "ElastioCfnRole"
  permission_model = "SERVICE_MANAGED"

  template_body = <<-EOT
    AWSTemplateFormatVersion: "2010-09-09"
    Description: "Create an IAM role for Elastio CloudFormation Deployment"
    Resources:
      PowerUserRole:
        Type: "AWS::IAM::Role"
        Properties:
          RoleName: "ElastioCfnRole"
          AssumeRolePolicyDocument:
            Version: "2012-10-17"
            Statement:
              - Effect: "Allow"
                Principal:
                  AWS: "*"
                Action: "sts:AssumeRole"
              - Effect: "Allow"
                Principal:
                  AWS: "${module.aws_lambda_function.lambda_role_arn}"
                Action: "sts:AssumeRole"
          Path: "/"
          ManagedPolicyArns:
            - "arn:aws:iam::aws:policy/AmazonS3FullAccess"
            - "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess"
            - "arn:aws:iam::aws:policy/IAMFullAccess"
            - "arn:aws:iam::aws:policy/CloudWatchFullAccess"
            - "arn:aws:iam::aws:policy/AmazonECS_FullAccess"
            - "arn:aws:iam::aws:policy/AWSCloudFormationFullAccess"
            - "arn:aws:iam::aws:policy/AWSLambda_FullAccess"
          Policies:
            - PolicyName: "ElastioCfnRolePolicy"
              PolicyDocument:
                Version: "2012-10-17"
                Statement:
                  - Effect: "Allow"
                    Action:
                      - "cloudformation:CreateStack"
                      - "cloudformation:DescribeStackEvents"
                      - "cloudformation:DescribeStackResources"
                      - "cloudformation:DescribeStacks"
                      - "cloudformation:GetStackPolicy"
                      - "cloudformation:GetTemplate"
                      - "cloudformation:GetTemplateSummary"
                      - "cloudformation:ListStackResources"
                      - "cloudformation:ListStacks"
                      - "cloudformation:UpdateStack"
                      - "servicecatalog:CreateProvisionedProduct"
                      - "servicecatalog:DescribeProduct"
                      - "servicecatalog:DescribeProvisionedProduct"
                      - "servicecatalog:DescribeProvisioningParameters"
                      - "servicecatalog:DescribeRecord"
                      - "servicecatalog:ListLaunchPaths"
                      - "servicecatalog:ListProvisionedProductPlans"
                      - "servicecatalog:ListProvisionedProductPlans"
                      - "servicecatalog:ListRecordHistory"
                      - "servicecatalog:ListServiceActionsForProvisioningArtifact"
                      - "servicecatalog:ProvisionProduct"
                      - "servicecatalog:SearchProducts"
                      - "servicecatalog:SearchProductsAsAdmin"
                      - "servicecatalog:SearchProvisionedProducts"
                      - "servicecatalog:TerminateProvisionedProduct"
                      - "servicecatalog:UpdateProvisionedProductProperties"
                      - "servicecatalog:UpdateProvisionedProduct"
                    Resource: "*"
    EOT

  auto_deployment {
    enabled                          = true
    retain_stacks_on_account_removal = false
  }

  capabilities = ["CAPABILITY_NAMED_IAM"]

  lifecycle {
    ignore_changes = [
      administration_role_arn,
    ]
  }
}

resource "aws_cloudformation_stack_set_instance" "elastio_cfn_role" {
  deployment_targets {
    organizational_unit_ids = data.aws_organizations_organization.this.roots[*].id
  }

  region         = local.aws_region
  stack_set_name = aws_cloudformation_stack_set.elastio_cfn_role.name
}
