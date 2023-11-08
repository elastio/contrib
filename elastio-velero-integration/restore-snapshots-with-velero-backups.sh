#!/bin/bash

if ! command -v jq &> /dev/null
  then
  echo
  echo "Please install jq before running this script."
  echo
  exit
fi

if ! command -v elastio &> /dev/null
  then
  echo
  echo "Please install elastio CLI before running this script."
  echo
  exit
fi

if ! command -v aws &> /dev/null
  then
  echo
  echo "Please install AWS CLI before running this script."
  echo
  exit
fi

if ! command -v gzip &> /dev/null
  then
  echo
  echo "Please install gzip before running this script."
  echo
  exit
fi

#usage info
usage(){
  echo "Usage:"
  echo "  $0 -n Namespace -b Velero-Backup-Name -s Velero-S3-Bucket -r AWS-Region"
  echo
  echo "Usage example:"
  echo "  $0 -n default -b daily-backup-20230919070049 -s velerobackupsbucket -r us-east-1"
  echo
  exit
}

if [ $# -lt 1 ]
then
  usage
fi

#parse options and arguments
while getopts "n:b:r:s:" opt
do
  case $opt in
    "n")
      namespaceName=$OPTARG
      ;;
    "b")
      veleroBackupName=$OPTARG
      ;;
    "r")
      region=$OPTARG
      ;;
    "s")
      veleroS3Bucket=$OPTARG
      ;;
    *)
      usage
      ;;
  esac
done

#set default AWS region
export AWS_DEFAULT_REGION=$region

if [ -z "$(aws s3 ls s3://$veleroS3Bucket/backups/$veleroBackupName/$veleroBackupName-volumesnapshots.json.gz)" ];
then
  echo
  echo "Make sure s3 bucket exists, velero backup name and region are correct."
  echo
  exit
fi

if [ -z $(aws ec2 describe-volumes --filters "Name=tag:kubernetes.io/created-for/pvc/namespace,Values=$namespaceName" --query "Volumes[].VolumeId" --output text) ];
then
  echo
  echo "Make sure namespace is correct. Please note namespace is case sensitive."
  echo
  exit
fi

echo
echo "Script started at $(date)"

#download velero config file from s3
echo
aws s3 cp s3://$veleroS3Bucket/backups/$veleroBackupName/$veleroBackupName-volumesnapshots.json.gz ./temp.json.gz
echo

#upload a backup of config to s3
output=$(aws s3 cp ./temp.json.gz s3://$veleroS3Bucket/backups/$veleroBackupName/$veleroBackupName-volumesnapshots-original-$(date +%s).json.gz  2>&1)

gzip -d temp.json.gz

for (( i = 0; i < $(cat temp.json | jq length); i++ ))
do
  volumeID=$(cat temp.json | jq .[$i].spec.providerVolumeID -r)
  snapshotID=$(cat temp.json | jq .[$i].status.providerSnapshotID -r)

  if [ $(aws ec2 describe-volumes --volume-ids $volumeID --query 'Volumes[].Tags[?Key==`kubernetes.io/created-for/pvc/namespace`].Value[]' --output text) = "$namespaceName" ]
  then
    if [ -z "$(aws ec2 describe-snapshots --snapshot-ids $snapshotID 2>/dev/null)" ];
    then

	  #get RP by namespace and volumeID
	  RP=$(elastio rp list --ebs $volumeID --limit 1000 | grep backup=$veleroBackupName | grep -oP rp-[A-Za-z0-9]+)

	  #exit if RPs not found
      if [ -z "$RP" ];
      then
        echo
        echo "Cannot find recovery point of $volumeID with tag $veleroBackupName."
        echo
	elastio version
        exit
      fi

	  echo "Restoring volume $volumeID($snapshotID) from elastio recovery point $RP."

	  output=$(elastio ebs restore --rp $RP --restore-asset-tags 2>&1)
    fi
  fi
done

#wait restore to finish
while [[ $(elastio job list --output-format json --kind restore) != "[]" ]]
do
  sleep 60
done

#create snapshots with velero tags
for volumeID in $(aws ec2 describe-volumes --filters Name=tag:velero.io/backup,Values=$veleroBackupName Name=tag:kubernetes.io/created-for/pvc/namespace,Values=$namespaceName --query "Volumes[].VolumeId" --output text)
do
  volumeTags=$(aws ec2 describe-volumes --volume-ids $volumeID | jq ".Volumes[0].Tags" | sed -r 's/"+//g' | sed -r 's/: +/=/g')
  snapshotID=$(aws ec2 create-snapshot --volume-id $volumeID --tag-specifications "ResourceType=snapshot,Tags=$volumeTags" --query "SnapshotId" --output text)
done

echo
echo "Creating EBS snapshot(s), the duration will depend on the data size."

#wait snapshot creation finish and remove EBS
for snapshotID in $(aws ec2 describe-snapshots --filters Name=tag:velero.io/backup,Values=$veleroBackupName Name=tag:kubernetes.io/created-for/pvc/namespace,Values=$namespaceName Name=tag:elastio:restored-from-rp,Values=* --query "Snapshots[].SnapshotId" --output text)
do
  while [[ $(aws ec2 describe-snapshots --snapshot-ids $snapshotID --query "Snapshots[].State" --output text) != "completed" ]]
  do
    sleep 60
  done
  aws ec2 delete-volume --volume-id $(aws ec2 describe-snapshots --snapshot-ids $snapshotID --query "Snapshots[].VolumeId" --output text)
done

echo
echo "Snapshot(s) created:"
s=0
for snapshotID in $(aws ec2 describe-snapshots --filters Name=tag:velero.io/backup,Values=$veleroBackupName Name=tag:kubernetes.io/created-for/pvc/namespace,Values=default Name=tag:elastio:restored-from-rp,Values=* --query "Snapshots[].SnapshotId" --output text)
do
  ((s++))
  echo $s. $snapshotID
done

#replace snapshot IDs with new values
declare -i v=0

for volumeID in $(cat temp.json | jq .[].spec.providerVolumeID -r)
do
  snapshotID=$(aws ec2 describe-snapshots --filters Name=tag:elastio:restored-from-asset,Values=$volumeID Name=tag:velero.io/backup,Values=$veleroBackupName Name=tag:kubernetes.io/created-for/pvc/namespace,Values=$namespaceName --query "Snapshots[].SnapshotId" --output text)
  if [ ! -z "$snapshotID" ];
  then
    cat temp.json | jq -c --arg snapshotID $snapshotID --argjson v $v '.[$v].status.providerSnapshotID |= $snapshotID' > volumesnapshots.json
    mv volumesnapshots.json temp.json
  fi
  ((v++))
done

mv temp.json $veleroBackupName-volumesnapshots.json

gzip $veleroBackupName-volumesnapshots.json

#upload updated config to s3
output=$(aws s3 cp ./$veleroBackupName-volumesnapshots.json.gz s3://$veleroS3Bucket/backups/$veleroBackupName/$veleroBackupName-volumesnapshots.json.gz)

rm $veleroBackupName-volumesnapshots.json.gz

echo
echo "Script finished at $(date)"
echo
