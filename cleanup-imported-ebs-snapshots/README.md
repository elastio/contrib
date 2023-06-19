# Lambda to cleanup EBS Snapshots imported to Elastio

## Garbage collection problem
Elastio has a feature to import AWS EBS snapshots of your volumes into recovery points inside its vault. When this is done you'll probably want to delete the original EBS snapshots to reduce costs. Once the EBS snapshots are imported to the Elastio vault, you can restore the data from there.

Elastio doesn't take responsibility for deleting the original EBS snapshots thus having a lower level of privileges required for its operation. Elastio, however, sets a tag named `elastio:imported-to-rp` when it is done with importing the EBS snapshot. The value of that tag is the ID of the recovery point the snapshot was imported as. This tag may be used for any purpose, including garbage collection.

To solve the problem of cleaning up the imported EBS snapshots you use may your own solution for this, or the one recommended in this article described below.

## Garbage collection solution

This repository provides a self-contained [CloudFormation stack template file](./cloudformation.yaml) that you can deploy in your region. This stack creates an AWS Lambda function scheduled to be run every hour. That function discovers all snapshots tagged with `elastio:imported-to-rp` tag and deletes them. It logs the number of snapshots that it discovered and also the IDs of snapshots that it deletes along with the information about the recovery point they were imported as.

The source code for the lambda function resides inside of `src/index.ts` file. The resulting code was compiled with the TypeScript compiler and inserted into the cloudformation template making it possible to deploy that template with a single AWS command. You may use the [`deploy.sh`](./deploy.sh) script to do the deployment via the AWS CLI.

The CloudFormation stack has several input parameters all set to default values to configure the tag, the maximum age, and the minimum number of snapshots to retain. These parameters are used to filter snapshots for deletion. For more details see the `cloudformation.json` template's `Parameters` section or deploy it via UI, where the parameters and their descriptions will be rendered.

If you need to do changes to the code of the lambda. See the section below.

## Building the lambda

This section will be useful if you need to make changes to the code of the lambda function.

The source code of the lambda is written in TypeScript in a single file `src/index.ts`. It is specifically all in one file to make it simple to paste it into the Cloudformation template afterwards.

Because the source code for the lambda function is written in a separate TypeScript there is a build step. First of all, install the dependencies. You need to do it only once.

```bash
npm install
```

Then run the build after you modify the code of the lambda function inside of `src/index.ts`.

```bash
npm run build
```

Then copy the output of thee JS file from the `dist/index.js` into the `cloudformation.json` file as the `InlineCode` property of the lambda function resource at the end of the template. Make sure to indent the code according to YAML syntax (the code must be two spaces deeper than the `InlineCode:` key).

Now you can deploy the resulting stack with the following bash script.

```
./deploy.sh
```


## Testing the lambda

There are some unit tests written for the logic of filtering the EBS snapshots. They can be run with the following commands.

```bash
# Build the original TypeScript file
npm run build

# Run the tests
npm run test
```
