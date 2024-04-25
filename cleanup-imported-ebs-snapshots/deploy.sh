#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

npm run build

code=$(cat dist/index.js) \
yq --inplace '.Resources.Lambda.Properties.InlineCode = strenv(code)' \
    cloudformation.yaml

set -x

aws cloudformation deploy --template-file cloudformation.yaml \
    --capabilities CAPABILITY_IAM \
    --stack-name elastio-imported-ebs-snapshots-cleanup-stack
