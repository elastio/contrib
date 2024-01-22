resource "aws_servicecatalog_organizations_access" "this" {
  enabled = "true"
}

resource "aws_servicecatalog_portfolio" "elastio_cfn" {
  name          = "DeployElastioCfn"
  description   = "Deploy Elastion CFN"
  provider_name = "AWS Service Catalog"
}

resource "aws_servicecatalog_portfolio_share" "elastio_cfn" {
  type              = "ORGANIZATION"
  portfolio_id      = aws_servicecatalog_portfolio.elastio_cfn.id
  principal_id      = data.aws_organizations_organization.this.arn
  share_principals  = true
  share_tag_options = true
}

resource "aws_servicecatalog_principal_portfolio_association" "allow_elastio_cfn_role" {
  portfolio_id   = aws_servicecatalog_portfolio.elastio_cfn.id
  principal_arn  = "arn:aws:iam:::role/ElastioCfnRole"
  principal_type = "IAM_PATTERN"
}

resource "aws_servicecatalog_product" "elastio_cfn" {
  name  = "DeployElastioCfn"
  owner = "Elastio"
  type  = "CLOUD_FORMATION_TEMPLATE"

  provisioning_artifact_parameters {
    template_url = local.cfn_template_initial_version
    type         = "CLOUD_FORMATION_TEMPLATE"
    name         = "Version 1"
  }
}

resource "aws_servicecatalog_product_portfolio_association" "elastio_cfn" {
  portfolio_id = aws_servicecatalog_portfolio.elastio_cfn.id
  product_id   = aws_servicecatalog_product.elastio_cfn.id
}

resource "aws_servicecatalog_provisioning_artifact" "elastio_cfn_v2" {
  for_each = local.cfn_templates

  name         = each.value.name
  description  = each.value.description
  template_url = each.value.template_url

  type       = "CLOUD_FORMATION_TEMPLATE"
  product_id = aws_servicecatalog_product.elastio_cfn.id
}
