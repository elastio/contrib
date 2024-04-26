# S3 Changelog

For large buckets, scanning all objects might take a lot of time. This CloudFormation template enables
the Changelog feature for S3 buckets, which significantly improves the scan performance after the initial
scan of the entire bucket is done.

This template deploys an SQS queue and an EventBridge rule which sends S3 update events to the queue.
Then, the Elastio `iscan` job reads those events to perform the scanning of new objects.

## Deploying the CFN stack

1. First, you need to enable Amazon EventBridge for your S3 buckets by following these instructions:
    [Enabling Amazon EventBridge](https://docs.aws.amazon.com/AmazonS3/latest/userguide/enable-event-notifications-eventbridge.html).
2. Use one of the following quick-create links. Choose the region where your Elastio Cloud Connector is deployed.

    **Important!** You can change the stack name, but it **MUST** start with `elastio-`. Otherwise, Elastio won't be able to access the created resources.

    * [us-east-1](https://us-east-1.console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/create/review?templateURL=https://elastio-prod-artifacts-us-east-2.s3.us-east-2.amazonaws.com/contrib/elastio-s3-changelog/v1/cloudformation-multiple-buckets.yaml&stackName=elastio-s3-changelog)
    * [us-east-2](https://us-east-2.console.aws.amazon.com/cloudformation/home?region=us-east-2#/stacks/create/review?templateURL=https://elastio-prod-artifacts-us-east-2.s3.us-east-2.amazonaws.com/contrib/elastio-s3-changelog/v1/cloudformation-multiple-buckets.yaml&stackName=elastio-s3-changelog)
    * [us-west-1](https://us-west-1.console.aws.amazon.com/cloudformation/home?region=us-west-1#/stacks/create/review?templateURL=https://elastio-prod-artifacts-us-east-2.s3.us-east-2.amazonaws.com/contrib/elastio-s3-changelog/v1/cloudformation-multiple-buckets.yaml&stackName=elastio-s3-changelog)
    * [us-west-2](https://us-west-2.console.aws.amazon.com/cloudformation/home?region=us-west-2#/stacks/create/review?templateURL=https://elastio-prod-artifacts-us-east-2.s3.us-east-2.amazonaws.com/contrib/elastio-s3-changelog/v1/cloudformation-multiple-buckets.yaml&stackName=elastio-s3-changelog)
    * [eu-central-1](https://eu-central-1.console.aws.amazon.com/cloudformation/home?region=eu-central-1#/stacks/create/review?templateURL=https://elastio-prod-artifacts-us-east-2.s3.us-east-2.amazonaws.com/contrib/elastio-s3-changelog/v1/cloudformation-multiple-buckets.yaml&stackName=elastio-s3-changelog)
    * [eu-west-1](https://eu-west-1.console.aws.amazon.com/cloudformation/home?region=eu-west-1#/stacks/create/review?templateURL=https://elastio-prod-artifacts-us-east-2.s3.us-east-2.amazonaws.com/contrib/elastio-s3-changelog/v1/cloudformation-multiple-buckets.yaml&stackName=elastio-s3-changelog)
    * [eu-west-2](https://eu-west-2.console.aws.amazon.com/cloudformation/home?region=eu-west-2#/stacks/create/review?templateURL=https://elastio-prod-artifacts-us-east-2.s3.us-east-2.amazonaws.com/contrib/elastio-s3-changelog/v1/cloudformation-multiple-buckets.yaml&stackName=elastio-s3-changelog)
    * [eu-west-3](https://eu-west-3.console.aws.amazon.com/cloudformation/home?region=eu-west-3#/stacks/create/review?templateURL=https://elastio-prod-artifacts-us-east-2.s3.us-east-2.amazonaws.com/contrib/elastio-s3-changelog/v1/cloudformation-multiple-buckets.yaml&stackName=elastio-s3-changelog)
    * [ca-central-1](https://ca-central-1.console.aws.amazon.com/cloudformation/home?region=ca-central-1#/stacks/create/review?templateURL=https://elastio-prod-artifacts-us-east-2.s3.us-east-2.amazonaws.com/contrib/elastio-s3-changelog/v1/cloudformation-multiple-buckets.yaml&stackName=elastio-s3-changelog)
    * [ap-south-1](https://ap-south-1.console.aws.amazon.com/cloudformation/home?region=ap-south-1#/stacks/create/review?templateURL=https://elastio-prod-artifacts-us-east-2.s3.us-east-2.amazonaws.com/contrib/elastio-s3-changelog/v1/cloudformation-multiple-buckets.yaml&stackName=elastio-s3-changelog)
    * [ap-southeast-2](https://ap-southeast-2.console.aws.amazon.com/cloudformation/home?region=ap-southeast-2#/stacks/create/review?templateURL=https://elastio-prod-artifacts-us-east-2.s3.us-east-2.amazonaws.com/contrib/elastio-s3-changelog/v1/cloudformation-multiple-buckets.yaml&stackName=elastio-s3-changelog)

3. Fill in the main parameters:
    * *BucketNames* - comma-separated list of S3 bucket names;

    * *ScanExistingObjects* - set to `true` if you want to perform the initial scan of all objects in the bucket(s);

    * *KeyPrefixes* - comma-separated list of prefixes of objects to scan. This will be applied to all buckets.
        If you want to use different prefixes for different buckets, you need to deploy multiple S3 Changelog stacks.
        Also, note that the paths selector in the Protection Policy will also be used to filter objects before scanning.
        This means that the *KeyPrefixes* parameter must be in sync with the paths selector in the Protection Policy,
        or not specified at all.

    > There are also some advanced and experimental parameters in the template, you can ignore them.

4. Check the box in front of `I acknowledge that AWS CloudFormation might create IAM resources with custom names`
    and `I acknowledge that AWS CloudFormation might require the following capability: CAPABILITY_AUTO_EXPAND`
    and click `Create stack`.

5. Create a [protection policy](https://docs.elastio.com/docs/tenant/policies#protection-policies) for your buckets in Elastio Tenant.
