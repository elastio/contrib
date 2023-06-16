# Lambda to cleanup EBS Snapshots imported to Elastio

## Garbage collection problem
Elastio has a feature to import AWS EBS snapshots of your volumes into recovery points inside its vault. When this is done you'll probably want to delete the original EBS snapshots to reduce costs. Once the EBS snapshots are imported to the Elastio vault, you can restore the data from there.

Elastio doesn't take responsibility for deleting the original EBS snapshots thus having a lower level of privileges required for its operation. Elastio, however, sets a tag named `"elastio:imported-to-rp"` when it is done with importing the EBS snapshot. The value of that tag is the ID of the recovery point the snapshot was imported as. This tag may be used for any purpose, including garbage collection.

To solve the problem of cleaning up the imported EBS snapshots you use may your own solution for this, or the one recommended in this article described below.

## Garbage collection solution

This repository provides a self-contained [CloudFormation stack template file](./cloudformation.yaml) thay you can deploy in your region. This stack creates an AWS Lambda function scheduled to be run every hour. That function discovers all snapshots tagged with `"elastio:imported-to-rp"` tag and deletes them. It logs the number of snapshots that it discovered and also the IDs of snapshots that it deletes along with the information about the recovery point they were imported as.

The source code for the lambda function resides inside of `src/index.ts` file. The resulting code was compiled with the TypeScript compiler and inserted into the cloudformation template making it possible to deploy that template with a single AWS command. You may use the [`deploy.sh`](./deploy.sh) script to do the deployment via the AWS CLI
