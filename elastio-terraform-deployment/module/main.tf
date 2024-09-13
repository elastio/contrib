locals {
  elastio_endpoint = "https://${var.elastio_tenant}/public-api/v1"
  headers = {
    Authorization = "Bearer ${var.elastio_pat}"
  }
}

data "http" "cloudformation_template" {
  url             = "${local.elastio_endpoint}/cloudformation-template"
  request_headers = local.headers

  retry {
    attempts     = 10
    max_delay_ms = 10000
  }

  lifecycle {
    postcondition {
      condition     = self.status_code >= 200 && self.status_code < 300
      error_message = "Failed to fetch CloudFormation template"
    }
  }
}

locals {
  global_acc_cfn_params = {
    encryptWithCmk = var.encrypt_with_cmk,
    globalManagedPolicies = (
      var.global_managed_policies == null
      ? null
      : join(",", var.global_managed_policies)
    ),
    globalPermissionBoundary  = var.global_permission_boundary,
    iamResourceNamesPrefix    = var.iam_resource_names_prefix
    iamResourceNamesSuffix    = var.iam_resource_names_suffix
    iamResourceNamesStatic    = var.iam_resource_names_static
    supportRoleExpirationDate = var.support_role_expiration_date
  }

  enriched_connectors = [
    for connector in var.elastio_cloud_connectors :
    merge(
      connector,
      {
        # Add the PascalCase version of the region name, because this is the
        # naming convention used in CFN parameters for regional settings.
        region_pascal = join(
          "",
          [for word in split("-", connector.region) : title(word)]
        )
      }
    )
  ]

  regional_acc_cfn_params = merge(
    [
      for connector in local.enriched_connectors :
      {
        "s3AccessLoggingTargetBucket${connector.region_pascal}"          = connector.s3_access_logging.target_bucket,
        "s3AccessLoggingTargetPrefix${connector.region_pascal}"          = connector.s3_access_logging.target_prefix,
        "s3AccessLoggingTargetObjectKeyFormat${connector.region_pascal}" = connector.s3_access_logging.target_object_key_format,
      }
      if connector.s3_access_logging != null
    ]
    ...
  )

  account_level_stack_params = {
    for key, value in merge(local.global_acc_cfn_params, local.regional_acc_cfn_params) :
    key => value
    if value != null
  }
}

resource "aws_cloudformation_stack" "elastio_account_level_stack" {
  name         = "elastio-account-level-stack"
  template_url = data.http.cloudformation_template.response_body
  tags = {
    "elastio:resource" = "true"
  }
  capabilities = ["CAPABILITY_NAMED_IAM"]
  parameters   = local.account_level_stack_params
}

resource "aws_cloudformation_stack" "elastio_nat_provision_stack" {
  count = var.elastio_nat_provision_stack == null ? 0 : 1

  name = "elastio-nat-provision-lambda"
  template_url = join(
    "/",
    [
      "https://elastio-prod-artifacts-us-east-2.s3.us-east-2.amazonaws.com",
      "contrib/elastio-nat-provision-lambda/${var.elastio_nat_provision_stack}",
      "cloudformation-lambda.yaml"
    ]
  )
  tags = {
    "elastio:resource" = "true"
  }
  capabilities = ["CAPABILITY_IAM"]
  parameters = {
    encryptWithCmk = var.encrypt_with_cmk
    lambdaTracing  = var.lambda_tracing
  }
}

data "aws_caller_identity" "current" {}

locals {
  elastio_cloud_connector_deploy_requests = [
    for connector in var.elastio_cloud_connectors : merge(
      connector,
      { account_id = data.aws_caller_identity.current.account_id },
    )
  ]
}

# resource "terraform_data" "elastio_cloud_connector" {
#   depends_on = [aws_cloudformation_stack.elastio_account_level_stack]

#   for_each = {
#     for request in local.elastio_cloud_connector_deploy_requests :
#     request.region => request
#   }

#   input            = each.value
#   triggers_replace = each.value

#   provisioner "local-exec" {
#     command = <<CMD
#       curl "$elastio_endpoint/deploy-cloud-connector" \
#         --location \
#         --fail-with-body \
#         --show-error \
#         --retry-all-errors \
#         --retry 5 \
#         -X POST \
#         -H "Authorization: Bearer $elastio_pat" \
#         -H "Content-Type: application/json; charset=utf-8" \
#         -d "$request_body"
#     CMD

#     environment = {
#       elastio_endpoint = local.elastio_endpoint
#       request_body     = jsonencode(self.input)

#       // Using nonsensitive() to workaround the problem that the script's
#       // output is entirely suppressed: https://github.com/hashicorp/terraform/issues/27154
#       elastio_pat = nonsensitive(var.elastio_pat)
#     }
#   }
# }
