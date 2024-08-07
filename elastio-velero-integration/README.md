This article provides a comprehensive guide on the backup and restore procedure for snapshots of EKS persistent storage created by Velero. 
Elastio efficiently reduces storage costs on AWS by effectively backing up and compressing data, while also providing enhanced protection against malware and ransomware threats.

## Requirements
- AWS CLI
- Elastio CLI
- jq tool

## Prerequisites
Before getting started, ensure that you have a Linux instance with Elastio and AWS CLI connected to your AWS account with Velero backups configured. Additionally, make sure to install the `jq` tool.

## Backup procedure

### Backup via Elastio Tenant
To create a backup policy that imports all snapshots corresponding to desired EBS volumes, you can follow these steps:

1. Access your Elastio Tenant.
2. Navigate to the Policies section.
3. Click on "New Policy" to start creating a new policy.
4. Provide a meaningful name for the policy.
5. Specify the appropriate schedule for the backups (e.g., daily, weekly, etc.) based on your requirements.
6. Select Integrity Scan options if required.
7. Add the desired EBS volumes that you want to include in the backups.
8. Configure additional options for the policy like on the screenshot below:
![image](https://github.com/elastio/contrib/assets/81738703/3f3e0103-806e-435e-870c-79b98caf5748)
9. Save the policy configuration.
   
Once the policy is created, Elastio will automatically import all the snapshots corresponding to the specified EBS volumes according to the defined schedule.

### Backup via Elastio CLI
To backup all snapshots associated with the EBS volume, simply execute the following command. Optionally you can include the `--iscan` parameter to enable vulnerability scanning for the backups.

```
elastio ebs import-snapshot --volume-id [Volume-id] --iscan
```

## Lambda to cleanup EBS Snapshots imported to Elastio
To set up a Lambda function for cleaning up snapshots imported by Elastio, please refer to the following [article](https://github.com/elastio/contrib/tree/master/cleanup-imported-ebs-snapshots).

## Automated restore procedure
`restore-snapshots-with-velero-backups.sh` script is designed to restore cleaned up snapshots from elastio vault.
To restore snapshots you need provide following parameters:
- -n Kubernetes namespace. To get the namespace name run `kubectl get namespaces`
- -b Velero backup name. To get the backup name run `velero get backups`
- -s S3 bucket for Velero backups. To get the bucket name run `velero backup-location get`
- -r AWS region with velero and elastio.

Usage example:
```
restore-snapshots-with-velero-backups.sh -n default -b daily-backup-20230919070049 -s velerobackupsbucket001 -r us-east-1
```

## Manual restore procedure
To verify that the desired backup snapshot has been imported by Elastio and removed from AWS, follow these steps:
1. Access your Elastio Tenant.
2. Navigate to the Assets list.
3. Locate and click on the EBS volume ID in the list.
4. In the opened backups list, identify the desired backup by checking the recovery points tags.

![image](https://github.com/elastio/contrib/assets/81738703/7a1eea5d-c5b3-4bad-a196-f0f22724feb3)

Copy recovery point ID and run the following command to restore EBS volume.

```
elastio ebs restore --rp [RP-ID] --restore-asset-tags --monitor
```
Replace [RP-ID] with the actual recovery point ID.

When restore is done set the following variables with the Velero backup name and bucket name with Velero backups.

```
export veleroBackupName=BackupName
export veleroS3Bucket=BucketName
export AWS_DEFAULT_REGION=AWSRegion
```
Replace `BackupName` and `BucketName` with corresponding names.

Retrieve the restored EBS volume ID and its tags using the following commands.

```
volumeID=$(aws ec2 describe-volumes --filters Name=tag:velero.io/backup,Values=$veleroBackupName --query "Volumes[0].VolumeId" --output text)
volumeTags=$(aws ec2 describe-volumes --volume-ids $volumeID | jq ".Volumes[0].Tags" | sed -r 's/"+//g' | sed -r 's/: +/=/g')
```

Create a snapshot of this volume and assigned the same tags to it.

```
snapshotID=$(aws ec2 create-snapshot --volume-id $volumeID --tag-specifications "ResourceType=snapshot,Tags=$volumeTags" --query "SnapshotId" --output text)
```

Modify the Velero backup description with new snapshot ID.

```
aws s3 cp s3://$veleroS3Bucket/backups/$veleroBackupName/$veleroBackupName-volumesnapshots.json.gz ./temp.json.gz

gzip -d temp.json.gz

cat temp.json | jq -c --arg snapshotID $snapshotID '.[0].status.providerSnapshotID |= $snapshotID' > $veleroBackupName-volumesnapshots.json

rm temp.json

gzip $veleroBackupName-volumesnapshots.json

aws s3 cp ./$veleroBackupName-volumesnapshots.json.gz s3://$veleroS3Bucket/backups/$veleroBackupName/$veleroBackupName-volumesnapshots.json.gz 

rm $veleroBackupName-volumesnapshots.json.gz 
```

Wait till snapshot creation is completed and proceed with the Velero restore process as you normally would.
