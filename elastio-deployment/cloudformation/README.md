# Elastio Cloudformation Deployment

This is an example of how you may automate the deployment of the Elastio stack in your AWS account.

## Obtain a Personal Access Token (PAT)

First of all, you'll need a secret PAT token to authenticate your Elastio installation with the Elastio Portal. You can generate one by following the steps below.

1. Open the [Elastio Portal](https://login.elastio.com/) in your web browser.
2. Go to the `Settings` page.
3. Open the `API access` tab.
4. Click on `Add New Access Token`.
5. Enter the name for the token, for example `Elastio deployment`.
6. Select the scope `Sources: Write` for the token.
7. Click on `Generate Token`.
8. Copy the generated token.
9. *Optional step.* Save the token in a secure place like 1Password or any other secret management system of your choice. This way you won't lose it.

## Use Elastio to Your Cloudformation Template

You can deploy the Elastio Connector Region stack using this Cloudformation quick-create URL. Make sure to replace the `{AWS_REGION}` with your region name:

https://{AWS_REGION}.console.aws.amazon.com/cloudformation/home?region={AWS_REGION}#/stacks/create/review?templateURL=https://elastio-prod-artifacts-{AWS_REGION}.s3.{AWS_REGION}.amazonaws.com/contrib/elastio-connector-deployer/v1/cloudformation-multiple-buckets.yaml&stackName=elastio-connector-region

Here is the bare Cloudformation template URL:

https://elastio-prod-artifacts-{AWS_REGION}.s3.{AWS_REGION}.amazonaws.com/contrib/elastio-connector-deployer/v1/cloudformation-multiple-buckets.yaml&stackName=elastio-connector-region

Specify the `ElastioTenant` and `ElastioPat` required parameters when deployment.
