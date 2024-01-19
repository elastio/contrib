# elastio-aws-org-elastio-cfn-deployment

With this solution you can easily bulk-deploy the Elastio CFN across your AWS organization.

Terraform code what implements it deploys a service catalog product, which is
shared across the org and could be used to deploy Elastio CFN stack in existing
accounts, also part of the code is a lambda that listens for new account
creation events and triggers a product provisioning in a new account.

## Requirements

- AWS
  - Control Tower should be configured along with Landing Zone
  - Make sure to run this code under credentials of the root aws account
- Tools
  - Python 3.6 or newer
  - zip
  - terraform 0.13 or newer
  - AWS CLI

## Usage

To deploy the solution run the following commands:

```console
terraform init
terraform plan
terraform apply
```

## Launching the product

_(Both CLI commands are supposed to be run under target account where the
Elastio CFN stack needs to be deployed)_

Provision product from the initial artifact:

```bash
#!/usr/bin/env bash

PRODUCT_NAME="DeployElastioCfn"

# Get the Product Id
PRODUCT_ID=$(aws servicecatalog search-products \
    --filters "FullTextSearch=$PRODUCT_NAME" \
    --query 'ProductViewSummaries[0].ProductId' --output text)

# Get the Provisioning Artifact Id of the initial version
INITIAL_ARTIFACT_ID=$(aws servicecatalog describe-product --id $PRODUCT_ID \
    --query 'ProvisioningArtifacts | sort_by(@, &CreatedTime)[0].Id' --output text)

# Generate a random suffix
RANDOM_SUFFIX=$(awk -v min=10000000 -v max=99999999 'BEGIN{srand(); print int(min+rand()*(max-min+1))}')
PROVISIONED_PRODUCT_NAME="$PRODUCT_NAME-$RANDOM_SUFFIX"

# Print the initial artifact id and the generated Provisioned Product Name
echo "Latest Artifact Id: $INITIAL_ARTIFACT_ID"
echo "Provisioned Product Name: $PROVISIONED_PRODUCT_NAME"

# Provision the product
aws servicecatalog provision-product \
    --product-id $PRODUCT_ID \
    --provisioning-artifact-id $INITIAL_ARTIFACT_ID \
    --provisioned-product-name $PROVISIONED_PRODUCT_NAME \
    --tags Key=elastio:resource,Value=true
```

Update provisioned product with latest version:

```bash
#!/usr/bin/env bash

PRODUCT_NAME="DeployElastioCfn"
PRODUCT_ID=$(aws servicecatalog search-products \
    --filters "FullTextSearch=$PRODUCT_NAME" \
    --query 'ProductViewSummaries[0].ProductId' --output text)

LATEST_ARTIFACT_ID=$(aws servicecatalog describe-product --id $PRODUCT_ID \
    --query 'ProvisioningArtifacts | sort_by(@, &CreatedTime)[-1].Id' --output text)

# We need to get the Provisioned Product name by looking up to DeployElastioCfn
# provisioned products, since it was generated with random suffix
PROVISIONED_PRODUCT_NAME=$(aws servicecatalog search-provisioned-products \
    --filters "SearchQuery=$PRODUCT_NAME" \
    --query 'ProvisionedProducts[0].Name' --output text)

# Update the product to the latest version
aws servicecatalog update-provisioned-product \
    --provisioned-product-name $PROVISIONED_PRODUCT_NAME \
    --provisioning-artifact-id $LATEST_ARTIFACT_ID \
    --product-name $PRODUCT_NAME \
    --tags Key=elastio:resource,Value=true
```
