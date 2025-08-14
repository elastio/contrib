#!/usr/bin/env python3
import boto3
import json
import os
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

def _merge_env_list(existing_list, to_add_dict):
    """existing_list: [{'name':..., 'value':...}], to_add_dict: {name: value}"""
    env_map = {e['name']: e.get('value', '') for e in (existing_list or [])}
    changed = False
    for k, v in to_add_dict.items():
        if env_map.get(k) != v:
            env_map[k] = v
            changed = True
    new_list = [{'name': k, 'value': v} for k, v in env_map.items()]
    return new_list, changed

def update_batch_jobs(bucket_name):
    # Correct env vars to add
    env_vars_to_add = {
        'ELASTIO_FORENSIC_ANALYSIS': 'TRUE',
        'ELASTIO_FORENSIC_ANALYSIS_ARCHIVAL_S3_BUCKET_NAME': bucket_name,
    }

    ec2 = boto3.client('ec2')
    regions = [r['RegionName'] for r in ec2.describe_regions()['Regions']]
    print(f"\n🌐 Found {len(regions)} AWS regions.")

    for region in regions:
        print(f"\n🌍 Checking region: {region}")
        batch = boto3.client('batch', region_name=region)

        try:
            paginator = batch.get_paginator('describe_job_definitions')
            pages = paginator.paginate(status='ACTIVE')
        except ClientError as e:
            print(f"⚠ Skipping region {region} due to error: {e}")
            continue

        for page in pages:
            for job_def in page.get('jobDefinitions', []):
                job_name = job_def.get('jobDefinitionName')
                revision = job_def.get('revision')
                if not job_name or not job_name.startswith("elastio"):
                    continue

                print(f"🔧 Evaluating job: {job_name}:{revision}")

                # Build a new definition preserving allowed top-level fields
                new_def = {
                    'jobDefinitionName': job_name,
                    'type': job_def['type'],
                }

                # Preserve important top-level fields if present
                for key in [
                    'parameters', 'retryStrategy', 'timeout', 'tags', 'propagateTags',
                    'schedulingPriority', 'nodeProperties', 'eksProperties',
                    'platformCapabilities'
                ]:
                    if key in job_def:
                        new_def[key] = job_def[key]

                changed_any = False

                # Container (EC2/Fargate) job defs
                if 'containerProperties' in job_def:
                    container_props = dict(job_def['containerProperties'])  # shallow copy
                    new_env, changed = _merge_env_list(container_props.get('environment', []), env_vars_to_add)
                    if changed:
                        container_props['environment'] = new_env
                        changed_any = True
                    new_def['containerProperties'] = container_props

                # EKS job defs
                if 'eksProperties' in job_def:
                    eks_props = dict(job_def['eksProperties'])
                    pod_props = dict(eks_props.get('podProperties', {}))
                    containers = [dict(c) for c in pod_props.get('containers', [])]
                    eks_changed = False
                    for c in containers:
                        new_env, changed = _merge_env_list(c.get('env', []), env_vars_to_add)
                        if changed:
                            c['env'] = new_env
                            eks_changed = True
                    if eks_changed:
                        pod_props['containers'] = containers
                        eks_props['podProperties'] = pod_props
                        changed_any = True
                    new_def['eksProperties'] = eks_props

                if not changed_any:
                    print("ℹ Env already up to date; skipping re-register.")
                    continue

                try:
                    resp = batch.register_job_definition(**new_def)
                    print(f"✅ Registered new revision: {resp['jobDefinitionArn']}")
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
