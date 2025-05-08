import boto3
import json
import os
import re
import argparse
from botocore.exceptions import ClientError
# -------------------------------
# Usage:
#
# python configure_forensics.py --bucket <bucket-name>
# -------------------------------


# -------------------------------
# Configuration
# -------------------------------
ROLE_PREFIXES = ["elastio-account-level-stack-", "elastio-account-level-sta-"]
ROLE_SUFFIXES = [
    "awsS3ScanBgJob", "awsFsxOntapScanBgJob", "awsEfsScanBgJob", "awsEc2ScanBgJob",
    "awsEbsSnapshotsScanBgJob", "awsEbsScanBgJob", "awsDrsSnapshotScanBgJob",
    "awsBackupRpVmScanBgJob", "awsBackupRpS3ScanBgJob", "awsBackupRpIscanBgJob",
    "awsBackupRpEfsScanBgJob", "awsBackupRpEc2ScanBgJob", "awsBackupRpEbsScanBgJob"
]
POLICY_FILENAME = "policy.json"

# -------------------------------
# Helpers
# -------------------------------
def get_account_id():
    return boto3.client("sts").get_caller_identity()["Account"]

def get_verified_roles(account_id):
    iam = boto3.client('iam')
    paginator = iam.get_paginator('list_roles')
    valid_arns = set()

    print(f"🔍 Scanning IAM roles in account {account_id}...\n")
    for page in paginator.paginate():
        for role in page['Roles']:
            role_name = role['RoleName']
            for prefix in ROLE_PREFIXES:
                for suffix in ROLE_SUFFIXES:
                    if role_name.startswith(prefix + suffix):
                        try:
                            iam.get_role(RoleName=role_name)
                            arn = f"arn:aws:iam::{account_id}:role/{role_name}"
                            valid_arns.add(arn)
                            print(f"✔ Valid role: {arn}")
                        except iam.exceptions.NoSuchEntityException:
                            print(f"✘ Skipped missing role: {role_name}")
                        except Exception as e:
                            print(f"⚠ Error checking {role_name}: {e}")
                        break
    return sorted(valid_arns)

def generate_policy(bucket_name, role_arns):
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": { "AWS": role_arns },
                "Action": ["s3:PutObject", "s3:PutObjectTagging"],
                "Resource": f"arn:aws:s3:::{bucket_name}/*"
            },
            {
                "Effect": "Allow",
                "Principal": { "AWS": role_arns },
                "Action": "s3:ListBucket",
                "Resource": f"arn:aws:s3:::{bucket_name}"
            }
        ]
    }

def save_policy_to_file(policy):
    with open(POLICY_FILENAME, "w") as f:
        json.dump(policy, f, indent=4)
    print(f"\n📁 Policy written to: {os.path.abspath(POLICY_FILENAME)}")

def update_batch_jobs(bucket_name):
    env_vars_to_add = [
        {'name': 'ELASTIO_FORENSIC_ANALYSIS_ARCHIVAL_ENABLED', 'value': 'TRUE'},
        {'name': 'ELASTIO_FORENSIC_ANALYSIS_ARCHIVAL_S3_BUCKET_NAME', 'value': bucket_name}
    ]

    ec2 = boto3.client('ec2')
    regions = [r['RegionName'] for r in ec2.describe_regions()['Regions']]
    print(f"\n🌐 Found {len(regions)} AWS regions.")

    for region in regions:
        print(f"\n🌍 Checking region: {region}")
        batch = boto3.client('batch', region_name=region)

        try:
            response = batch.describe_job_definitions(status='ACTIVE')
            job_definitions = response['jobDefinitions']
        except ClientError as e:
            print(f"⚠ Skipping region {region} due to error: {e}")
            continue

        if not job_definitions:
            print("No active job definitions found.")
            continue

        for job_def in job_definitions:
            job_name = job_def['jobDefinitionName']
            revision = job_def['revision']

            if job_name.startswith("elastio"):
                print(f"🔧 Updating job: {job_name}:{revision}")

                container_props = job_def['containerProperties']
                existing_env = container_props.get('environment', [])

                env_dict = {env['name']: env['value'] for env in existing_env}
                for new_env in env_vars_to_add:
                    env_dict[new_env['name']] = new_env['value']
                updated_env = [{'name': k, 'value': v} for k, v in env_dict.items()]

                sanitized_props = {
                    k: v for k, v in container_props.items() if k != 'networkConfiguration'
                }
                sanitized_props['environment'] = updated_env

                try:
                    response = batch.register_job_definition(
                        jobDefinitionName=job_name,
                        type=job_def['type'],
                        containerProperties=sanitized_props
                    )
                    print(f"✅ Registered new revision: {response['jobDefinitionArn']}")
                except ClientError as e:
                    print(f"❌ Failed to register {job_name} in {region}: {e}")

    print("\n🎉 Multi-region job update completed.")

# -------------------------------
# Entry Point
# -------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Configure S3 bucket policy and enable forensic archival.")
    parser.add_argument("--bucket", type=str, default="elastio-forensic", help="S3 bucket name")
    args = parser.parse_args()
    bucket_name = args.bucket

    print(f"\n🚀 Starting configuration for bucket: {bucket_name}")

    account_id = get_account_id()
    role_arns = get_verified_roles(account_id)

    if not role_arns:
        print("❌ No valid roles found. Exiting.")
    else:
        policy = generate_policy(bucket_name, role_arns)
        print("\n✅ Generated policy:\n")
        print(json.dumps(policy, indent=4))
        save_policy_to_file(policy)

        update_batch_jobs(bucket_name)
