import boto3
import csv
import logging
from botocore.exceptions import ClientError
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

# --- CONFIGURATION ---
CROSS_ACCOUNT_ROLE = "OrganizationAccountAccessRole" 
TARGET_REGIONS = None  # Set to specific list like ['us-east-1'] for speed, or None for all
OUTPUT_FILE = "aws_full_storage_audit.csv"
# ---------------------

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

def get_org_accounts():
    """Fetches all active accounts in the Organization."""
    org_client = boto3.client('organizations')
    accounts = []
    paginator = org_client.get_paginator('list_accounts')
    try:
        for page in paginator.paginate():
            for acct in page['Accounts']:
                if acct['Status'] == 'ACTIVE':
                    accounts.append(acct)
    except ClientError as e:
        logger.error(f"Could not list accounts: {e}")
    return accounts

def get_session_for_account(account_id, role_name, region=None):
    """Assumes role into member account and returns a boto3 session."""
    try:
        # Check if we are already in the target account (e.g. running from Master)
        current_id = boto3.client('sts').get_caller_identity()['Account']
        if current_id == account_id:
            return boto3.Session(region_name=region)

        # Otherwise assume role
        sts_client = boto3.client('sts')
        role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
        response = sts_client.assume_role(
            RoleArn=role_arn,
            RoleSessionName="StorageAuditSession"
        )
        creds = response['Credentials']
        return boto3.Session(
            aws_access_key_id=creds['AccessKeyId'],
            aws_secret_access_key=creds['SecretAccessKey'],
            aws_session_token=creds['SessionToken'],
            region_name=region
        )
    except ClientError as e:
        logger.warning(f"Skipping {account_id}: {e}")
        return None

def get_regions(session):
    if TARGET_REGIONS:
        return TARGET_REGIONS
    try:
        ec2 = session.client('ec2', region_name='us-east-1')
        return [r['RegionName'] for r in ec2.describe_regions()['Regions']]
    except Exception:
        return ['us-east-1']

def scan_region(session, region, account_id):
    """Scans a specific region for EBS, RDS, EFS, FSx, and S3."""
    data = []
    
    # --- 1. EBS Volumes ---
    try:
        ec2 = session.client('ec2', region_name=region)
        paginator = ec2.get_paginator('describe_volumes')
        for page in paginator.paginate():
            for vol in page['Volumes']:
                data.append({
                    'Account': account_id, 'Region': region, 'Service': 'EBS',
                    'Type': vol['VolumeType'], 'Size_GB': vol['Size'],
                    'Identifier': vol['VolumeId']
                })
    except Exception: pass

    # --- 2. RDS Instances ---
    try:
        rds = session.client('rds', region_name=region)
        paginator = rds.get_paginator('describe_db_instances')
        for page in paginator.paginate():
            for db in page['DBInstances']:
                data.append({
                    'Account': account_id, 'Region': region, 'Service': 'RDS',
                    'Type': db['StorageType'], 'Size_GB': db['AllocatedStorage'],
                    'Identifier': db['DBInstanceIdentifier']
                })
    except Exception: pass

    # --- 3. EFS File Systems ---
    try:
        efs = session.client('efs', region_name=region)
        # EFS describe_file_systems paginator is cleaner than raw calls
        paginator = efs.get_paginator('describe_file_systems')
        for page in paginator.paginate():
            for fs in page['FileSystems']:
                # SizeInBytes contains 'Value' (Total) and 'Timestamp'
                size_gb = fs['SizeInBytes']['Value'] / (1024**3)
                data.append({
                    'Account': account_id, 'Region': region, 'Service': 'EFS',
                    'Type': f"EFS-{fs.get('PerformanceMode', 'General')}",
                    'Size_GB': round(size_gb, 2),
                    'Identifier': fs['FileSystemId']
                })
    except Exception: pass

    # --- 4. FSx File Systems ---
    try:
        fsx = session.client('fsx', region_name=region)
        paginator = fsx.get_paginator('describe_file_systems')
        for page in paginator.paginate():
            for fs in page['FileSystems']:
                # FSx StorageCapacity is always in GiB
                data.append({
                    'Account': account_id, 'Region': region, 'Service': 'FSx',
                    'Type': f"FSx-{fs['FileSystemType']}", # WINDOWS, LUSTRE, ONTAP, OPENZFS
                    'Size_GB': fs['StorageCapacity'],
                    'Identifier': fs['FileSystemId']
                })
    except Exception: pass

    # --- 5. S3 (Via CloudWatch) ---
    try:
        cw = session.client('cloudwatch', region_name=region)
        metrics = cw.list_metrics(
            Namespace='AWS/S3', MetricName='BucketSizeBytes',
            Dimensions=[{'Name': 'StorageType', 'Value': 'StandardStorage'}]
        )
        for metric in metrics['Metrics']:
            bucket_name = next((d['Value'] for d in metric['Dimensions'] if d['Name'] == 'BucketName'), "Unknown")
            stats = cw.get_metric_statistics(
                Namespace='AWS/S3', MetricName='BucketSizeBytes',
                Dimensions=metric['Dimensions'],
                StartTime=datetime.utcnow() - timedelta(days=2),
                EndTime=datetime.utcnow(), Period=86400, Statistics=['Average']
            )
            if stats['Datapoints']:
                latest = sorted(stats['Datapoints'], key=lambda x: x['Timestamp'])[-1]
                data.append({
                    'Account': account_id, 'Region': region, 'Service': 'S3',
                    'Type': 'StandardStorage',
                    'Size_GB': round(latest['Average'] / (1024**3), 2),
                    'Identifier': bucket_name
                })
    except Exception: pass

    return data

def process_account(account):
    """Worker to process an account."""
    account_id = account['Id']
    logger.info(f"Scanning Account: {account['Name']} ({account_id})")
    
    session = get_session_for_account(account_id, CROSS_ACCOUNT_ROLE)
    if not session: return []

    regions = get_regions(session)
    results = []
    
    with ThreadPoolExecutor(max_workers=5) as region_executor:
        future_to_region = {region_executor.submit(scan_region, session, r, account_id): r for r in regions}
        for future in as_completed(future_to_region):
            results.extend(future.result())
            
    return results

def main():
    logger.info("Starting AWS Storage Audit (EBS, RDS, EFS, FSx, S3)...")
    accounts = get_org_accounts()
    
    all_data = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_account = {executor.submit(process_account, acct): acct for acct in accounts}
        for future in as_completed(future_to_account):
            all_data.extend(future.result())

    if all_data:
        keys = ["Account", "Region", "Service", "Type", "Size_GB", "Identifier"]
        with open(OUTPUT_FILE, 'w', newline='') as output_file:
            dict_writer = csv.DictWriter(output_file, keys)
            dict_writer.writeheader()
            dict_writer.writerows(all_data)
        logger.info(f"Done. Report saved to {OUTPUT_FILE}")
    else:
        logger.warning("No data found.")

if __name__ == "__main__":
    main()
