# S3 Changelog

This CloudFormation template enables the Changelog feature for S3 buckets.
It deploys an SQS queue and an EventBridge rule which sends S3 update events to the queue.
Then, the Elastio `iscan` job reads those events to perform the scanning of new objects.

There are a couple of scenarios where this feature can be useful:

* Incremental S3 scanning. For large buckets, scanning all objects might take a lot of time.
    The changelog queue allows the scanning of only new objects in the bucket, significantly improving the
    scan performance after the initial scan of the entire bucket is done.
* Quasi-realtime scanning (QRTS). Instead of running scan jobs according to a schedule in the Protection
    Policy, Elastio can scan new objects in an S3 bucket continuously. As new S3 object change events
    arrive at the changelog queue, the `iscan` job is scheduled shortly after, allowing for
    near-realtime scanning.

## Deploying the CFN stack

1. First, you need to enable Amazon EventBridge for your S3 buckets by following these instructions:
    [Enabling Amazon EventBridge](https://docs.aws.amazon.com/AmazonS3/latest/userguide/enable-event-notifications-eventbridge.html).
2. You can use
    [this quick-create link](https://us-east-2.console.aws.amazon.com/cloudformation/home?region=us-east-2#/stacks/create/review?templateURL=https://elastio-artifacts-kskorokhodov-us-east-2.s3.us-east-2.amazonaws.com/cloudformation.yaml&stackName=elastio-s3-changelog)
    to create the stack.

    > You might need to switch to the region where your Elastio CloudFormation stack is deployed.

    >**Important!** If you want to change the stack name, make sure it starts from `elastio-`. Otherwise, Elastio won't be able to access the created resources.

3. Fill in the parameters:
    * *BucketNames* - comma-separated list of S3 bucket names;
    * *EnableQrts* - set to `true` if you want to enable the quasi-realtime scanning. Note that there should be no
        scheduled scans enabled in the Protection Policies for these buckets if the QRTS is enabled;
    * *KeyPrefixes* - comma-separated list of prefixes of objects to scan. This will be applied to all buckets.
        If you want to use different prefixes for different buckets, you need to deploy multiple S3 Changelog stacks.
        Also note that, unless QRTS is enabled, the paths selector in the Protection Policy will also be used to filter
        objects before scanning. This means that the *KeyPrefixes* parameter must be in sync with the paths selector
        in the Protection Policy, or not specified at all;
    * *ScanExistingObjects* - set to `true` if you want to perform the initial scan of all objects in the buckets.

4. Check the checkmarks in front of "I acknowledge that AWS CloudFormation might create IAM resources with custom names"
    and "I acknowledge that AWS CloudFormation might require the following capability: CAPABILITY_AUTO_EXPAND"
    and click "Create stack".

5. If you haven't enabled QRTS, [create a protection policy](https://docs.elastio.com/docs/tenant/policies#protection-policies)
    for your buckets in Elastio Tenant.
