import boto3
import json
import os
import argparse
from botocore.exceptions import ClientError

ROLE_PREFIXES = ["elastio-account-level-stack-", "elastio-account-level-sta-"]
ROLE_SUFFIXES = [
    "awsS3ScanBgJob", "awsFsxOntapScanBgJob", "awsEfsScanBgJob", "awsEc2ScanBgJob",
    "awsEbsSnapshotsScanBgJob", "awsEbsScanBgJob", "awsDrsSnapshotScanBgJob",
    "awsBackupRpVmScanBgJob", "awsBackupRpS3ScanBgJob", "awsBackupRpIscanBgJob",
    "awsBackupRpEfsScanBgJob", "awsBackupRpEc2ScanBgJob", "awsBackupRpEbsScanBgJob"
]
POLICY_FILENAME = "policy.json"

def get_account_id():
    return boto3.client("sts").get_caller_identity()["Account"]

def bucket_exists(bucket_name):
    s3 = boto3.client('s3')
    try:
        s3.head_bucket(Bucket=bucket_name)
        return True
    except ClientError as e:
        code = e.response['Error']['Code']
        if code in ['404', 'NoSuchBucket']:
            return False
        elif code == '403':
            print(f"⚠ Access denied to bucket: {bucket_name} (may exist in another account)")
            return True
        else:
            raise

def create_bucket(bucket_name):
    session = boto3.session.Session()
    region = session.region_name or 'us-east-1'
    s3 = session.client('s3')

    try:
        if region == 'us-east-1':
            s3.create_bucket(Bucket=bucket_name)
        else:
            s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': region}
            )
        print(f"✅ Created bucket: {bucket_name} in region {region}")
    except ClientError as e:
        print(f"❌ Failed to create bucket: {bucket_name}\nReason: {e}")
        raise

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

def apply_policy_to_bucket(bucket_name, policy):
    s3 = boto3.client('s3')
    try:
        s3.put_bucket_policy(Bucket=bucket_name, Policy=json.dumps(policy))
        print(f"✅ Successfully applied policy to bucket: {bucket_name}")
    except ClientError as e:
        print(f"❌ Failed to apply policy to bucket: {bucket_name}\nReason: {e}")

def collect_elastio_job_names():
    ec2 = boto3.client('ec2')
    regions = [r['RegionName'] for r in ec2.describe_regions()['Regions']]
    job_names = set()

    print("\n🔍 Collecting Elastio job definitions across all regions...")
    for region in regions:
        try:
            batch = boto3.client('batch', region_name=region)
            response = batch.describe_job_definitions(status='ACTIVE')
            for jd in response.get('jobDefinitions', []):
                name = jd['jobDefinitionName']
                if name.startswith("elastio"):
                    job_names.add(name)
        except ClientError as e:
            print(f"⚠ Error collecting from region {region}: {e}")
    return list(job_names), regions

def update_batch_jobs(bucket_name):
    job_names, regions = collect_elastio_job_names()
    if not job_names:
        print("❌ No Elastio job definitions found.")
        return

    env_vars_to_add = [
        {'name': 'ELASTIO_FORENSIC_ANALYSIS_ARCHIVAL_ENABLED', 'value': 'TRUE'},
        {'name': 'ELASTIO_FORENSIC_ANALYSIS_ARCHIVAL_S3_BUCKET_NAME', 'value': bucket_name}
    ]

    print(f"\n🛠 Updating job definitions for {len(job_names)} jobs across {len(regions)} regions...")
    for region in regions:
        print(f"\n🌍 Region: {region}")
        batch = boto3.client('batch', region_name=region)
        for job_name in job_names:
            try:
                defs = batch.describe_job_definitions(jobDefinitionName=job_name, status='ACTIVE')
                if not defs['jobDefinitions']:
                    continue

                # Get the latest revision
                latest_def = sorted(defs['jobDefinitions'], key=lambda d: d['revision'], reverse=True)[0]

                # Use jobDefinitionName and find the matching revision
                all_defs = batch.describe_job_definitions(jobDefinitionName=latest_def['jobDefinitionName'])['jobDefinitions']
                full_def = next((d for d in all_defs if d['revision'] == latest_def['revision']), None)

                if not full_def:
                    print(f"❌ Could not find full definition for {job_name}:{latest_def['revision']}")
                    continue

                container_props = full_def['containerProperties']
                existing_env = container_props.get('environment', [])
                env_dict = {env['name']: env['value'] for env in existing_env}
                for new_env in env_vars_to_add:
                    env_dict[new_env['name']] = new_env['value']
                updated_env = [{'name': k, 'value': v} for k, v in env_dict.items()]
                container_props['environment'] = updated_env

                # Remove fields not accepted in registration
                for field in ['jobDefinitionArn', 'revision', 'status']:
                    full_def.pop(field, None)

                response = batch.register_job_definition(
                    jobDefinitionName=full_def['jobDefinitionName'],
                    type=full_def['type'],
                    parameters=full_def.get('parameters', {}),
                    containerProperties=container_props,
                    retryStrategy=full_def.get('retryStrategy', {}),
                    timeout=full_def.get('timeout', {}),
                    platformCapabilities=full_def.get('platformCapabilities', []),
                    tags=full_def.get('tags', {})
                )
                print(f"✅ Updated {job_name} -> {response['jobDefinitionArn']}")
            except ClientError as e:
                print(f"❌ Failed to update {job_name} in {region}: {e}")

    print("\n🎉 Completed updating job definitions in all regions.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Configure S3 bucket policy and enable forensic archival.")
    parser.add_argument("--bucket", type=str, default="elastio-forensic", help="S3 bucket name")
    args = parser.parse_args()
    bucket_name = args.bucket

    print(f"\n🚀 Starting configuration for bucket: {bucket_name}")

    if bucket_exists(bucket_name):
        print(f"🪣 Bucket already exists: {bucket_name}")
    else:
        print(f"📦 Bucket {bucket_name} not found. Creating it...")
        create_bucket(bucket_name)

    account_id = get_account_id()
    role_arns = get_verified_roles(account_id)

    if not role_arns:
        print("❌ No valid roles found. Exiting.")
    else:
        policy = generate_policy(bucket_name, role_arns)
        print("\n✅ Generated policy:\n")
        print(json.dumps(policy, indent=4))
        save_policy_to_file(policy)
        apply_policy_to_bucket(bucket_name, policy)
        update_batch_jobs(bucket_name)
