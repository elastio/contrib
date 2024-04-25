#!/usr/bin/env bash
#
# This is a script that updates the labmda source code in the CFN template from the
# lambda.js file where it's easier to edit and maintain. Then it deploys the CFN
# stack with the updated lambda code for testing.
#
# You need yq and AWS CLI set up.

set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

code=$(cat lambda.js) \
yq --inplace '.Resources.EBSVolumeCleanupFunction.Properties.InlineCode = strenv(code)' \
    cleanup-elastio-ebs-vols.yaml

set -x

aws cloudformation deploy --template-file cleanup-elastio-ebs-vols.yaml \
    --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
    --stack-name elastio-cleanup-elastio-ebs-volumes
