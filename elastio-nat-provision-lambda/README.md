# NAT Gateway Provision Lambda

This CloudFormation template deploys a lambda function with EventBridge rules that automatically
provision a NAT Gateway when Elastio worker EC2 instances are starting, and de-provisions it
when they are not running anymore.

The lambda will provision one NAT Gateway and Elastic IP per VPC, and configure the route table
of the subnet where Elastio worker instances are running to route all traffic through the NAT Gateway.
Note there is a default limit of 5 Elastic IP addresses per AWS region, and there should be at least one
address available when the lambda deploys the NAT Gateway.

The lambda will only provision a NAT Gateway if Elastio workers are running in a private subnet,
and there is at least one public subnet in the same availability zone in the same VPC. There must
be no route `0.0.0.0/0` configured in the route table of the private subnet.

## Deploying the CFN stack

1. Use one of the following quick-create links. Choose the region where your Elastio Cloud Connector is deployed.

    * [us-east-1](https://us-east-1.console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/create/review?templateURL=https://elastio-prod-artifacts-us-east-2.s3.us-east-2.amazonaws.com/contrib/elastio-nat-provision-lambda/v5/cloudformation-lambda.yaml&stackName=elastio-nat-provision-lambda)
    * [us-east-2](https://us-east-2.console.aws.amazon.com/cloudformation/home?region=us-east-2#/stacks/create/review?templateURL=https://elastio-prod-artifacts-us-east-2.s3.us-east-2.amazonaws.com/contrib/elastio-nat-provision-lambda/v5/cloudformation-lambda.yaml&stackName=elastio-nat-provision-lambda)
    * [us-west-1](https://us-west-1.console.aws.amazon.com/cloudformation/home?region=us-west-1#/stacks/create/review?templateURL=https://elastio-prod-artifacts-us-east-2.s3.us-east-2.amazonaws.com/contrib/elastio-nat-provision-lambda/v5/cloudformation-lambda.yaml&stackName=elastio-nat-provision-lambda)
    * [us-west-2](https://us-west-2.console.aws.amazon.com/cloudformation/home?region=us-west-2#/stacks/create/review?templateURL=https://elastio-prod-artifacts-us-east-2.s3.us-east-2.amazonaws.com/contrib/elastio-nat-provision-lambda/v5/cloudformation-lambda.yaml&stackName=elastio-nat-provision-lambda)
    * [eu-central-1](https://eu-central-1.console.aws.amazon.com/cloudformation/home?region=eu-central-1#/stacks/create/review?templateURL=https://elastio-prod-artifacts-us-east-2.s3.us-east-2.amazonaws.com/contrib/elastio-nat-provision-lambda/v5/cloudformation-lambda.yaml&stackName=elastio-nat-provision-lambda)
    * [eu-west-1](https://eu-west-1.console.aws.amazon.com/cloudformation/home?region=eu-west-1#/stacks/create/review?templateURL=https://elastio-prod-artifacts-us-east-2.s3.us-east-2.amazonaws.com/contrib/elastio-nat-provision-lambda/v5/cloudformation-lambda.yaml&stackName=elastio-nat-provision-lambda)
    * [eu-west-2](https://eu-west-2.console.aws.amazon.com/cloudformation/home?region=eu-west-2#/stacks/create/review?templateURL=https://elastio-prod-artifacts-us-east-2.s3.us-east-2.amazonaws.com/contrib/elastio-nat-provision-lambda/v5/cloudformation-lambda.yaml&stackName=elastio-nat-provision-lambda)
    * [eu-west-3](https://eu-west-3.console.aws.amazon.com/cloudformation/home?region=eu-west-3#/stacks/create/review?templateURL=https://elastio-prod-artifacts-us-east-2.s3.us-east-2.amazonaws.com/contrib/elastio-nat-provision-lambda/v5/cloudformation-lambda.yaml&stackName=elastio-nat-provision-lambda)
    * [ca-central-1](https://ca-central-1.console.aws.amazon.com/cloudformation/home?region=ca-central-1#/stacks/create/review?templateURL=https://elastio-prod-artifacts-us-east-2.s3.us-east-2.amazonaws.com/contrib/elastio-nat-provision-lambda/v5/cloudformation-lambda.yaml&stackName=elastio-nat-provision-lambda)
    * [ap-south-1](https://ap-south-1.console.aws.amazon.com/cloudformation/home?region=ap-south-1#/stacks/create/review?templateURL=https://elastio-prod-artifacts-us-east-2.s3.us-east-2.amazonaws.com/contrib/elastio-nat-provision-lambda/v5/cloudformation-lambda.yaml&stackName=elastio-nat-provision-lambda)
    * [ap-southeast-1](https://ap-southeast-1.console.aws.amazon.com/cloudformation/home?region=ap-southeast-1#/stacks/create/review?templateURL=https://elastio-prod-artifacts-us-east-2.s3.us-east-2.amazonaws.com/contrib/elastio-nat-provision-lambda/v5/cloudformation-lambda.yaml&stackName=elastio-nat-provision-lambda)
    * [ap-southeast-2](https://ap-southeast-2.console.aws.amazon.com/cloudformation/home?region=ap-southeast-2#/stacks/create/review?templateURL=https://elastio-prod-artifacts-us-east-2.s3.us-east-2.amazonaws.com/contrib/elastio-nat-provision-lambda/v5/cloudformation-lambda.yaml&stackName=elastio-nat-provision-lambda)

2. Check the box in front of `I acknowledge that AWS CloudFormation might create IAM resources`
    and click `Create stack`.

## Deployer IAM role

If you'd like to automate the deployment of the NAT Gateway Provision Lambda Cloudformation stack, then you can use the example IAM role and policies to assign to your deployer process IAM identity. The example is available at [`deployer/main.tf`](./deployer/main.tf).

## Updating the CFN stack

To update the existing CFN stack use the Cloudformation UI or AWS CLI and pass the following CFN template link to replace the existing template:
```
https://elastio-prod-artifacts-us-east-2.s3.us-east-2.amazonaws.com/contrib/elastio-nat-provision-lambda/v5/cloudformation-lambda.yaml
```
