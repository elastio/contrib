#!/usr/bin/env bash

# Upload the templates into your S3 bucket for testing
# Use this script like this:
# ```bash
# elastio_tenant='...'
# elastio_pat='...'
#
# link_params=(
#     "&param_ElastioPat=${elastio_pat}"
#     "&param_ElastioTenant=${elastio_tenant}"
# )
#
# S3_BUCKET_PREFIX=bucket \
# LINK_PARAMS="$(printf '%s' "${link_params[@]}")" \
# ./upload.sh
# ```

set -euxo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

export AWS_PAGER=""

s3_key_prefix=contrib/elastio-deployment/cloudformation

trap cleanup SIGINT SIGTERM ERR EXIT

temp_dir=$(mktemp -d)

echo "Creating temp dir $temp_dir"

function cleanup {
    # Unset the trap to prevent an infinite loop
    trap - SIGINT SIGTERM ERR EXIT

    echo "Cleaning up $temp_dir"

    rm -rf "$temp_dir"
}

version=$(cat version)

AWS_REGION=${AWS_REGION:-us-east-2}

cp ./*.yaml "$temp_dir"

zip "$temp_dir/lambda.zip" ./lambda.py

cd "$temp_dir"

# Using `|` separator instead of `/` for prefix, because prefix
# by itself contains a `/`
sed -i ./*.yaml \
    -e "s/{{S3_BUCKET_PREFIX}}/$S3_BUCKET_PREFIX/g" \
    -e "s|{{S3_KEY_PREFIX}}|$s3_key_prefix|g" \
    -e "s/{{VERSION}}/$version/g"

aws s3 cp --recursive ./ "s3://$S3_BUCKET_PREFIX-$AWS_REGION/${s3_key_prefix}/${version}/"


if [[ -v UPDATE_LAMBDA_ONLY ]]; then
    aws lambda update-function-code \
        --function-name elastio-nat-gateway-provision \
        --s3-bucket "$S3_BUCKET_PREFIX-$AWS_REGION" \
        --s3-key "$s3_key_prefix/$version/lambda.zip"
    exit 0
fi

# Skip opening the link if we're on CI
if [[ -v CI ]]; then
    exit 0
fi

cfn_deep_link_parts=(
    "https://$AWS_REGION.console.aws.amazon.com/cloudformation/home"
    "?region=$AWS_REGION#/stacks/create/review?templateURL="
    "https://$S3_BUCKET_PREFIX-$AWS_REGION.s3.$AWS_REGION.amazonaws.com/"
    "$s3_key_prefix/$version/connector.yaml"
    "&stackName=elastio-connector"
    "${LINK_PARAMS:-}"
)

cfn_deep_link=$(IFS="" ; echo "${cfn_deep_link_parts[*]}")

# Open the stack in the AWS Console
xdg-open "$cfn_deep_link"
