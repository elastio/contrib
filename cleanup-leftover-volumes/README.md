# Lambda to Cleanup Left-over EBS Volumes

Normally Elastio automatically cleans up all resources after a successful or failed operation.  However there's a very
specific case in which the temporary EBS volume we ingest can't be deleted due to an EBS limitation.  In such a case
this Lambda can provide an automated back-stop to clean up left-over EBS volumes no matter what.

To deploy this Lambda function, run the following AWS CLI command in the account and region where Elastio is deployed:

```shell
aws cloudformation deploy --template-file cleanup-elastio-ebs-vols.yaml \
    --stack-name ElastioEBSVolumeCleanupStack \
    --capabilities CAPABILITY_IAM \
    --region us-east-1 \
    --no-fail-on-empty-changeset \
    --no-execute-changeset
```

Be sure to replace `us-east-1` with the region you want, or remove the `--region` argument entirely to use the default
region in your AWS config.


