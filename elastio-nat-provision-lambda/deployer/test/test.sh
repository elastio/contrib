#!/usr/bin/env bash

set -euxo pipefail

role=ElastioNatProvisionLambdaDeployer
account=$(aws sts get-caller-identity --query 'Account' --output text)
role_arn="arn:aws:iam::${account}:role/${role}"

output=$(aws sts assume-role --role-arn "$role_arn" --role-session-name vkryvenko)

AWS_REGION=$(aws configure get region || echo us-east-2)
export AWS_REGION

AWS_ACCESS_KEY_ID=$(echo "$output" | jq -r '.Credentials.AccessKeyId')
export AWS_ACCESS_KEY_ID

AWS_SECRET_ACCESS_KEY=$(echo "$output" | jq -r '.Credentials.SecretAccessKey')
export AWS_SECRET_ACCESS_KEY

AWS_SESSION_TOKEN=$(echo "$output" | jq -r '.Credentials.SessionToken')
export AWS_SESSION_TOKEN

unset AWS_PROFILE

terraform apply -auto-approve
terraform destroy -auto-approve
