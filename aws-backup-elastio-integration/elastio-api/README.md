# Elastio API for AWS Backup integration

Elastio connector stack provides JSON API based on AWS Lambda to integrate with the AWS Backup service. It covers the use cases described below.

## Use cases

### Import an AWS Backup recovery point in an Elastio vault

An encrypted, and compressed copy of your data can be efficiently imported into an Elastio vault. It is treated the same as any other Elastio recovery point created by Elastio itself, meaning that you can restore it, scan it, etc.

### AWS Backup restore testing validation

Elastio can scan the resource created as part of AWS Backup restore testing. The temporarily restored resource may be modified by Elastio directly for better performance and optimized cost. For example, Elastio stops the restored EC2 instance, detaches its volumes and attaches them to the worker EC2 instance that performs the scan.

> ❗Elastio never modifies customer's production data. IAM permissions restrict Elastio to mutating only resources managed by Elastio itself. All such resources have `elastio:resource=true` tag. During regular operation of Elastio all data is treated as sensitive and Elastio can only read and create snapshots of resources. AWS Backup restore testing is an exception where a temporarily restored resource is created and handed to the scanning software to battle-test it.

For Elastio to be able to modify the temporarily restored resource, you must grant explicit permission. This must done by adding a tag `elastio:resource=true` to the restored resource.


## Lambda API

Elastio connector stack deploys an AWS Lambda function named `elastio-bg-jobs-service-aws-backup-integration`. You can use the synchronous lambda `Invoke` API to send it a request payload in JSON format. The schema of the JSON request is described below.

### Request

```jsonc
{
  // Name of the source AWS Backup vault.
  // It is assumed that the vault is in the same account and region as Elastio connector.
  //
  // Required.
  "aws_backup_vault": "Default",

  // ARN of the source AWS Backup recovery point
  //
  // Required.
  "aws_backup_rp_arn": "arn:aws:ec2:eu-central-1::snapshot/snap-069324f1f1b639172",

  // Name of the target `elastio` vault. It determines in what subnets Elastio
  // runs the job worker. For import operations it also determines where Elastio
  // stores the imported RP.
  //
  //
  // Optional. If omitted or `null` then the default vault is used.
  "elastio_vault": "elastio-vault-name",

  // Specifies the action Elastio should perform.
  //
  // # Possible values
  //
  // - `ingest-and-scan` (default): import the AWS Backup RP into Elastio and then scan it
  //
  // - `scan`: scan the AWS Backup RP or temporarily restored resource directly
  //           without importing it into Elastio
  //
  // - `ingest`: import the AWS Backup RP into Elastio without scanning it
  //
  // Optional. If omitted, the value will be read from an SSM parameter named
  // `/elastio/aws-backup-integration-mode`. If that parameter is absent then
  // the default specified above will be used.
  "action": "ingest-and-scan",

  // Options related to scanning.
  //
  // Optional. If omitted then iscan is disabled. Required only when `action`
  // is set to `scan`.
  "iscan": {
    // Optional. If omitted then ransomware scan is disabled.
    "ransomware": true,

    // Optional. If omitted then malware scan is disabled.
    "malware": true,

    // Name of the event bus scan reports will be written to.
    //
    // Optional. If omitted, the value will be read from an SSM parameter named
    // `/elastio/iscan-results-eventbridge-bus/`. If that parameter is absent then
    // the 'Default' event bus is used.
    "event_bridge_bus": "MyBusName",

    // An opaque string that is simply sent in the resulting `EventBridge` scan
    // results event. This can be used for forwarding custom context from the
    // component that initiates the scan, to the component that processes its results.
    //
    // Optional.
    "user_data": "my user data",
  },

  // In AWS Backup recovery test scenario, contains the ID of the temporarily
  // restored resource created from the AWS Backup recovery point.
  //
  // It may be one of the following:
  // - EFS filesystem ID. Example: `fs-0f7c4cb255b35a06d`
  // - S3 bucket name. Example: `my.bucket.name`
  // - EC2 instance ID. Example: `i-017dfa5f7736a0c58`
  // - EBS volume ID. Example: `vol-054c3d699f1667fa9`
  //
  // This restored resource is used for reading the data. However, the reported
  // scan results will be associated with the originally backed up resource,
  // that is discovered from the AWS Backup recovery point metadata.
  //
  // # Treatment of the temporarily restored resource for different types of RPs
  //
  // # S3
  // The restored resource is required to be specified. Elastio only reads data
  // from the restored bucket and doesn't modify it.
  //
  // To assist in efficient scanning of the bucket you can deploy a an S3 changelog
  // SQS event queue, that Elastio will use to do scanning of the bucket in parallel
  // with its restore process for maximum performance. See details in the paragraph
  // 'Scanning S3 in parallel with restoring'.
  //
  // # EFS
  // The restored resource is required to be specified. Elastio only reads data
  // from the restored FS and doesn't modify it.
  //
  // # EC2
  // This parameter is optional. If it is not specified Elastio reads the data
  // from the snapshots of the volumes of the AMI managed by AWS Backup.
  //
  // If this parameter is specified Elastio stops the restored EC2 instance,
  // detaches its volumes and attaches them to its own worker instance that
  // performs the scan.
  //
  // # EBS
  // This parameter is optional. If not specified Elastio reads the data from
  // the snapshot of the volume managed by AWS Backup.
  //
  // If this parameter is specified Elastio attaches the restored volume to
  // its worker instance that performs the scan.
  "restored_resource_id": "fs-0f7c4cb255b35a06d",
}
```

### Response

```jsonc
{
  // Describes the AWS Backup rp job that was submitted.
  //
  // Required.
  "job_state": { /* See `job_state` description bellow */ },
}
```

The `job_state` is a sum type of two shapes. Either one of them can be returned:

```jsonc
{
    // Serves as a discriminator of this shape.
    // Indicates that a new background job was started to import the requested AWS Backup RP.
    //
    // Required.
    "kind": "Created",

    // ID of the started Elastio background job.
    //
    // Required.
    "job_id": "j-01ghkcq8g409rxg35x1st6vdzp",

    // Abort token that is used to grant access to aborting the Elastio background job.
    //
    // Required.
    "abort_token": "ew64dYAJt5eXlig4j38zY3K++4OPWomo3tdR/lNxE5I="
}
```
```jsonc
{
    // Serves as a discriminator of this shape.
    // Indicates that no new background job was started as a result of this request,
    // because there is an already running job that does what you need.
    //
    // Required.
    "kind": "Existing",

    // ID of the existing Elastio background job that was already in the process of
    // performing the requested action.
    //
    // Required.
    "job_id": "j-01ghkcq8g409rxg35x1st6vdzp",
}
```

## Scanning S3 in parallel with restoring

Scanning of large S3 bucket can take a lot of time and resources. When AWS Backup restore
testing job creates a temporary bucket Elastio can start scanning it immediately. To be
able to do this Elastio requires an additional component that assists in getting changelog
data from S3 while AWS Backup is restoring the bucket.

### Elastio S3 changelog

Elastio S3 changelog Cloudformation stack implements this component. It deploys an SQS queue
and an EventBridge subscription for it that forwards events from the target S3 bucket.
Documentation for Elastio S3 changelog is available [here](https://github.com/elastio/contrib/tree/master/elastio-s3-changelog).

The documentation at the provided link describes the use case of incremental scanning of multiple buckets. However, for AWS Backup restore testing validation of S3 it's possible to use a lighter-weight version of the Cloudformation
stack that serves just for a single S3 bucket.


The template `cloudformation-single-bucket.yaml` implements a special case of a stack for a single bucket. Use this [quick-create link](https://us-east-2.console.aws.amazon.com/cloudformation/home?region=us-east-2#/stacks/create/review?templateURL=https://elastio-prod-artifacts-us-east-2.s3.us-east-2.amazonaws.com/contrib/elastio-s3-changelog/v1/cloudformation-single-bucket.yaml&stackName=elastio-s3-changelog) to experiment with this stack. Its final template artifact developed by Elastio is always available under the following S3 link: <https://elastio-prod-artifacts-us-east-2.s3.us-east-2.amazonaws.com/contrib/elastio-s3-changelog/v1/cloudformation-single-bucket.yaml>. You can use this template URL when deploying the stack in production.

Elastio's AWS Backup integration lambda can automatically discover the S3 changelog from the deployed stack, and use it if it is present. You don't need to pass any additional parameters in the JSON request to the lambda. Just make sure the stack is created at the beginning of the restore testing validation process and exists while it is running.

Elastio doesn't delete the S3 changelog Cloudformation stack automatically, so make sure you delete it once the restore testing validation is done.


### Stack parameters

To configure the stack specifically for restore testing you should use the following parameters for the `CreateStack` Cloudformation API.

```jsonc
{
  // The name of the stack **must** begin with `elastio`. This is important for IAM
  // access of Elastio Connector to this stack. The rest of name is not important,
  // but the following format is recommended
  "StackName": "elastio-s3-changelog-{bucket_name_hash_here}",

  // Tags are also used for providing IAM access for Elastio Connector to this stack.
  // It's important that you set them on this stack
  "Tags": [
    {
      "Key": "elastio:resource",
      "Value": "true"
    }
  ],

  // You may use this exact link. It is maintained by Elastio and guaranteed to
  // be stable providing a compatible stack at any time.
  "TemplateURL": "https://elastio-prod-artifacts-us-east-2.s3.us-east-2.amazonaws.com/contrib/elastio-s3-changelog/v1/cloudformation-single-bucket.yaml",

  "Parameters": [
    {
      // Specify the name of the temporarily restored bucket here
      "ParameterKey": "BucketName",
      "ParameterValue": "{bucket_name_here}"
    },
    {
      // We want Elastio to scan the entire bucket, so ask Elastio to discover
      // the objects that were already restored in the bucket before the S3
      // changelog stack was created
      "ParameterKey": "ScanExistingObjects",
      "ParameterValue": "true"
    },
    {
      // Dead letter queue for S3 changelog is not needed for AWS Backup restore
      // testing validation
      "ParameterKey": "EnableDlq",
      "ParameterValue": "false"
    },
  ]
}
```

### Enabling S3 Eventbridge notifications

S3 changelog requires that S3 object change events are reported by the restored bucket to EventBridge. You need to enable them on the bucket before deploying the stack. You can do this by following [these instructions](https://docs.aws.amazon.com/AmazonS3/latest/userguide/enable-event-notifications-eventbridge.html).

### Notifying Elastio scan job of the end of restore

Elastio scan job needs to know when to stop scanning the temporarily restored bucket, otherwise it listens for S3 changelog events awaiting for new objects to appear in the bucket. You can send the following event in JSON format to the S3 changelog SQS queue to notify Elastio scanner that it should stop waiting for new updates and finish its scanning report:

```json
{
  "kind": "EndOfEvents"
}
```

The URL of the SQS queue to send the event to can be discovered by describing the outputs of S3 changelog Cloudformation stack. The name of the output is `queueUrl`. Example of how to obtain it with AWS CLI:

```bash
aws cloudformation describe-stacks \
  --stack-name elastio-s3-changelog-foo \
  --query 'Stacks[0].Outputs[? OutputKey == `queueUrl`].OutputValue' \
  --output text
```
