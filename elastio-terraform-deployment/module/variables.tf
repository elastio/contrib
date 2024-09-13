variable "elastio_pat" {
  description = "Personal Access Token generated by the Elastio Portal"
  sensitive   = true
  type        = string
  nullable    = false
}

variable "elastio_tenant" {
  description = "Name of your Elastio tenant. For example `mycompany.app.elastio.com`"
  type        = string
  nullable    = false
}

variable "elastio_cloud_connectors" {
  description = <<DESCR
    List of regions where Cloud Connectors are to be deployed, VPC and subnet(s) to use,
    and other regional configurations (mostly for regulatory compliance).
  DESCR

  type = list(object({
    region     = string
    vpc_id     = string
    subnet_ids = list(string)

    s3_access_logging = optional(object({
      target_bucket = string
      target_prefix = optional(string)

      # Can be one of the following:
      # - SimplePrefix
      # - PartitionedPrefix:EventTime
      # - PartitionedPrefix:DeliveryTime
      target_object_key_format = optional(string)
    }))
  }))

  nullable = false
  default  = []
}

variable "elastio_nat_provision_stack" {
  description = <<DESCR
    Specifies the version of Elastio NAT provision stack to deploy (e.g. `v4`).

    This is a Cloudformation stack that automatically provisions NAT Gateways in
    your VPC when Elastio worker instances run to provide them with the outbound
    Internet access when Elastio is deployed in private subnets.

    If you don't need this stack (e.g. you already have NAT gateways in your VPC
    or you deploy into public subnets) you can omit this parameter. The default
    value of `null` means there won't be any NAT provision stack deployed.

    The source code of this stack can be found here:
    https://github.com/elastio/contrib/tree/master/elastio-nat-provision-lambda
  DESCR

  type     = string
  nullable = true
  default  = null
}

variable "encrypt_with_cmk" {
  description = <<DESCR
    Provision additional customer-managed KMS keys to encrypt
    Lambda environment variables, DynamoDB tables, S3. Note that
    by default data is encrypted with AWS-managed keys.

    Enable this option only if your compliance requirements mandate the usage of CMKs.

    If this option is disabled Elastio creates only 1 CMK per region where
    the Elastio Connector stack is deployed. If this option is enabled then
    Elastio creates 1 KMS key per AWS account and 2 KMS keys per every AWS
    region where Elastio is deployed in your AWS account.

    If you have `elastio_nat_provision_stack` enabled as well, then 1 more KMS key
    will be created as part of that stack as well (for a total of 3 KMS keys per region).

  DESCR

  default = null
}

variable "lambda_tracing" {
  description = <<DESCR
    Enable AWS X-Ray tracing for Lambda functions. This increases the cost of
    the stack. Enable only if needed
  DESCR
  type        = bool
  default     = null
}

variable "global_managed_policies" {
  description = "List of IAM managed policies ARNs to attach to all Elastio IAM roles"
  type        = list(string)
  default     = null
}

variable "global_permission_boundary" {
  description = "The ARN of the IAM managed policy to use as a permission boundary for all Elastio IAM roles"
  type        = string
  default     = null
}

variable "iam_resource_names_prefix" {
  description = <<DESCR
    Add a custom prefix to names of all IAM resources deployed by this stack.
    The sum of the length of the prefix and suffix must not exceed 14 characters.
  DESCR

  type    = string
  default = null
}

variable "iam_resource_names_suffix" {
  description = <<DESCR
    Add a custom prefix to names of all IAM resources deployed by this stack.
    The sum of the length of the prefix and suffix must not exceed 14 characters.
  DESCR

  type    = string
  default = null
}

variable "iam_resource_names_static" {
  description = <<DESCR
    If enabled, the stack will use static resource names without random characters in them.

    This parameter is set to `true` by default, and it shouldn't be changed. The older
    versions of Elastio stack used random names generated by Cloudformation for IAM
    resources, which is inconvenient to work with. New deployments that use the terraform
    automation should have this set to `true` for easier management of IAM resources.
  DESCR

  type     = bool
  default  = true
  nullable = false
}

variable "disable_customer_managed_iam_policies" {
  description = <<DESCR
    If this is set to `false` (or omitted), then the stack will create
    additional customer-managed IAM policies that you can attach to your
    IAM identities to grant them direct access to the Elastio Connector stack.
    This way you can use elastio CLI directly to list Elastio scan jobs or
    submit new scan jobs. Set this to `true` if you don't need these policies.
  DESCR

  type    = bool
  default = null
}

variable "support_role_expiration_date" {
  description = <<DESCR
    Specifies a date when the ElastioSupport role will be disabled. This role
    contains only the permissions necessary for managing the resources deployed
    by Elastio and it grants no write access to the resources owned by you.
    If this role is enabled Elastio will be able to provide support for this
    Connector to keep it in a healthy state. However, if you don't want this
    role to be enabled, leave this empty. To enable this support role but only
    for a defined period of time, enter an expiration date and time in this field,
    in which case Elastio support personnel will be able to use this role but only
    until the specified date.
    The date must be in the format YYYY-MM-DDTHH:MM:SSZ.
    Example value: 2020-04-01T14:20:30Z.
  DESCR

  type    = string
  default = null
}
