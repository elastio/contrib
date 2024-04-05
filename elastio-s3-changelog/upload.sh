#!/usr/bin/env bash

# Upload the templates into your S3 bucket for testing
# Use this script like this:
# ```bash
# S3_BUCKET=bucket LINK_PARAMS='&param_BucketNames=foo,bar' ./elastio-s3-changelog/upload.sh
# ```

set -euxo pipefail

s3_prefix=contrib/elastio-s3-changelog

trap cleanup SIGINT SIGTERM ERR EXIT

temp_dir=$(mktemp -d)

echo "Creating temp dir $temp_dir"

function cleanup {
    # Unset the trap to prevent an infinite loop
    trap - SIGINT SIGTERM ERR EXIT

    echo "Cleaning up $temp_dir"

    rm -rf "$temp_dir"
}

cd elastio-s3-changelog

version=$(cat version)

AWS_REGION=${AWS_REGION:-us-east-2}

cp ./*.yaml "$temp_dir"

cd "$temp_dir"

# Using `|` separator instead of `/` for prefix, because prefix
# by itself contains a `/`
sed -i ./*.yaml \
    -e "s/{{AWS_REGION}}/$AWS_REGION/g" \
    -e "s/{{S3_BUCKET}}/$S3_BUCKET/g" \
    -e "s|{{S3_PREFIX}}|$s3_prefix|g" \
    -e "s/{{VERSION}}/$version/g"

aws s3 cp --recursive ./ "s3://${S3_BUCKET}/${s3_prefix}/${version}/"

# Skip opening the link if we're on CI
if [[ -v CI ]]; then
    exit 0
fi

cfn_deep_link_parts=(
    "https://$AWS_REGION.console.aws.amazon.com/cloudformation/home"
    "?region=$AWS_REGION#/stacks/create/review?templateURL="
    "https://$S3_BUCKET.s3.$AWS_REGION.amazonaws.com/"
    "$s3_prefix/$version/cloudformation-multiple-buckets.yaml"
    "&stackName=elastio-s3-changelog"
    "${LINK_PARAMS:-}"
)

cfn_deep_link=$(IFS="" ; echo "${cfn_deep_link_parts[*]}")

# Open the stack in the AWS Console
xdg-open "$cfn_deep_link"
