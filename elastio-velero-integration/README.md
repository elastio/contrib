This article provides a comprehensive guide on the backup and restore procedure for snapshots of EKS persistent storage created by Velero. 
Elastio, a powerful tool, efficiently reduces storage costs on AWS by effectively backing up and compressing data.

## Requirements
- AWS CLI
- Elastio CLI
- jq tool

## Prerequisites
Before getting started, ensure that you have a Linux instance with Elastio and AWS CLI connected to your AWS account with Velero backups configured. Additionally, make sure to install the `jq` tool.

## Backup procedure

### Backup via Elastio Tenant
TODO: Add description here when functionality will be implemented on blue stack.

### Backup via Elastio CLI
To backup all snapshots associated with the EBS volume, simply execute the following command. Optionally you can include the `--iscan` parameter to enable vulnerability scanning for the backups.

```
elastio ebs import-snapshot --volume-id [Volume-id] --iscan
```

## TODO: Add lambda desctiption for snapshots removal

## Restore procedure
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
```
Replace `BackupName` and `BucketName` with coresponding names.

Retrieve the restored EBS volume ID and its tags using the following commands.

```
volumeID=$(aws ec2 describe-volumes --filters Name=tag:velero.io/backup,Values=$veleroBackupName --query "Volumes[0].VolumeId" --output text)
volumeTags=$(aws ec2 describe-volumes --volume-ids $volumeID | jq ".Volumes[0].Tags" | sed -r 's/"+//g' | sed -r 's/: +/=/g')
```

Create a snapshot of this volume and assigned the same tags to it.

```
snapshotID=$(aws ec2 create-snapshot --volume-id $volumeID --tag-specifications "ResourceType=snapshot,Tags=$tags" --query "SnapshotId" --output text)
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

Proceed with the Velero restore process as you normally would.
