#!/usr/bin/env bash

set -euo pipefail

project_dir=$(readlink -f $(dirname $0))

aws cloudformation deploy --template-file $project_dir/cloudformation.yaml \
    --capabilities CAPABILITY_IAM \
    --stack-name elastio-imported-ebs-snapshots-cleanup-stack
