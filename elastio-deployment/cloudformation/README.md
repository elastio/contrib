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
9. _Optional step._ Save the token in a secure place like 1Password or any other secret management system of your choice. This way you won't lose it.

You'll need to specify this PAT token as an input for the Cloudformation deployment described below.

## Deploy Elastio Cloudformation Templates

1. Open the [Elastio Portal](https://login.elastio.com/) in your web browser.
2. Go to the `Settings` page.
3. Open the `Deployments` tab.
4. Click on `Deploy`.
5. The UI here is designed for manual deployment where you know the AWS account ID and regions you're going to deploy into beforehand. For our use case, set `AWS Account ID` to some arbitrary value like `123456789123`, then select an arbitrary region for the stack, and then select any AWS region for the regional coverage.
6. Click on `Next`.
7. Right-click on `Review Elastio CFN`.
8. Click on `Copy link address`.

Now you have the URL for the Elastio Connector Account Cloudformation template. This Cloudformation stack must be deployed only once in a single region in your AWS account. You can deploy it manually or you can combine it with additional Cloudformation templates offered in this folder that simplify the deployment of the Connector Account and other required stacks for your.

The other stacks required for Elastio operation are called Connector Region stacks. These stacks must be installed into every region that you want to cover with Elastio scanning.

Let's see how you can automate the deployment of the Connector Account and Connector Region stacks next.

### Provided Automation

There are two Cloudformation templates, and you should choose the one that fits your use case:

- `connector-region.yaml` deploys only a Connector Region stack
- `connector.yaml` deploys both Connector Account and Connector Region stacks

If you are planning to deploy a Connector only in a single region you can use the `connector.yaml` Cloudformation template, that will install everything you need in a single stack.

If you are planning to deploy a Connector in many regions, then you'll need to deploy the Connector Account Cloudformation stack yourself. Only _after that deployment is done_, you can deploy `connector-region.yaml` stacks into the regions you want to cover.

If you are deploying the Connector Account stack manually, you should set the name of the stack to `elastio-account-level-stack` and assign a tag `elastio:stack:connector-account` to it.

Here are some links to the released versions of both Cloudformation templates.

> [!WARNING]
> The single-click deployment links below are configured with the `us-east-1` region.
> Make sure to switch to your desired region of deployment after you follow them.

### `connector.yaml` template

- [Single-click deployment link](https://us-east-1.console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/create/review?templateURL=https://elastio-prod-artifacts-us-east-1.s3.us-east-1.amazonaws.com/contrib/elastio-deployment/cloudformation/v2/connector.yaml&stackName=elastio-connector)
- [Template download link](https://elastio-prod-artifacts-us-east-1.s3.us-east-1.amazonaws.com/contrib/elastio-deployment/cloudformation/v2/connector.yaml)

### `connector-region.yaml` template

- [Single-click deployment link](https://us-east-1.console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/create/review?templateURL=https://elastio-prod-artifacts-us-east-1.s3.us-east-1.amazonaws.com/contrib/elastio-deployment/cloudformation/v2/connector-region.yaml&stackName=elastio-connector-region)
- [Template download link](https://elastio-prod-artifacts-us-east-1.s3.us-east-1.amazonaws.com/contrib/elastio-deployment/cloudformation/v2/connector-region.yaml)
