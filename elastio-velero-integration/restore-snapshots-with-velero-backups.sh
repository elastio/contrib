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

#check if snapshots exist
if [ ! -z "$(aws ec2 describe-snapshots --filters Name=tag:velero.io/backup,Values=$veleroBackupName Name=tag:kubernetes.io/created-for/pvc/namespace,Values=$namespaceName --query "Snapshots[].SnapshotId" --output text)" ];
then
  echo
  echo "Cannot proceed. Script is designed to restore entire namespace from a given backup. Snapshots with velero backup $veleroBackupName and namespace $namespaceName are present in AWS:"
  s=0
  for snapshotID in $(aws ec2 describe-snapshots --filters Name=tag:velero.io/backup,Values=$veleroBackupName Name=tag:kubernetes.io/created-for/pvc/namespace,Values=$namespaceName --query "Snapshots[].SnapshotId" --output text)
  do
    ((s++))
    echo $s. $snapshotID
  done
  exit
fi

#get RPs by namespace and velero backup name
RPs=($(elastio rp list --limit 1000 --tag velero.io/backup=$veleroBackupName | grep namespace=$namespaceName | grep -oP rp-[A-Za-z0-9]+))

#exit if RPs not found
if [ -z "$RPs" ];
then
  echo
  echo "No elastio recovery points matching your request were found. Make sure namespace and velero backup name are correct."
  echo
  exit
fi

echo
echo $(date)": Found elastio recovery points:"
r=0
for RP in ${RPs[*]}
do
  ((r++))
  echo $r. $RP
done

#run restore of RPs
for RP in ${RPs[*]}
do
  sleep 2
  var=$(elastio ebs restore --rp $RP --restore-asset-tags 2>&1)
done

echo
echo $(date)": EBS restore is in progress, the duration will depend on the data size."

sleep 60

#wait restore to finish
while [[ $(elastio job list --output-format json --kind restore) != "[]" ]]
do
  sleep 60
  echo -ne "."
done

#create snapshots with velero tags
for volumeID in $(aws ec2 describe-volumes --filters Name=tag:velero.io/backup,Values=$veleroBackupName Name=tag:kubernetes.io/created-for/pvc/namespace,Values=$namespaceName --query "Volumes[].VolumeId" --output text)
do
  volumeTags=$(aws ec2 describe-volumes --volume-ids $volumeID | jq ".Volumes[0].Tags" | sed -r 's/"+//g' | sed -r 's/: +/=/g')
  snapshotID=$(aws ec2 create-snapshot --volume-id $volumeID --tag-specifications "ResourceType=snapshot,Tags=$volumeTags" --query "SnapshotId" --output text)
done

echo
echo $(date)": EBS restore is completed."
echo
echo $(date)": Creating EBS snapshot(s), the duration will depend on the data size."

#wait snapshot creation finish and remove EBS
for snapshotID in $(aws ec2 describe-snapshots --filters Name=tag:velero.io/backup,Values=$veleroBackupName Name=tag:kubernetes.io/created-for/pvc/namespace,Values=$namespaceName Name=tag:elastio:restored-from-rp,Values=* --query "Snapshots[].SnapshotId" --output text)
do
  while [[ $(aws ec2 describe-snapshots --snapshot-ids $snapshotID --query "Snapshots[].State" --output text) != "completed" ]]
  do
    sleep 60
    echo -ne "."
  done
  aws ec2 delete-volume --volume-id $(aws ec2 describe-snapshots --snapshot-ids $snapshotID --query "Snapshots[].VolumeId" --output text)
done

echo
echo $(date)": Snapshot(s) created:"
s=0
for snapshotID in $(aws ec2 describe-snapshots --filters Name=tag:velero.io/backup,Values=$veleroBackupName Name=tag:kubernetes.io/created-for/pvc/namespace,Values=$namespaceName Name=tag:elastio:restored-from-rp,Values=* --query "Snapshots[].SnapshotId" --output text)
do
  ((s++))
  echo $s. $snapshotID
done

echo
echo $(date)": Updating Velero configuration file."
echo

#download velero config file from s3
aws s3 cp s3://$veleroS3Bucket/backups/$veleroBackupName/$veleroBackupName-volumesnapshots.json.gz ./temp.json.gz

echo

#upload a backup of config to s3
aws s3 cp ./temp.json.gz s3://$veleroS3Bucket/backups/$veleroBackupName/$veleroBackupName-volumesnapshots-original-$(date +%s).json.gz

gzip -d temp.json.gz

#replace snapshot IDs with new values
declare -i v=0

for volumeID in $(cat temp.json | jq .[].spec.providerVolumeID -r)
do
  snapshotID=$(aws ec2 describe-snapshots --filters Name=tag:elastio:restored-from-asset,Values=$volumeID Name=tag:velero.io/backup,Values=$veleroBackupName Name=tag:kubernetes.io/created-for/pvc/namespace,Values=$namespaceName --query "Snapshots[].SnapshotId" --output text)
  echo -ne "."
  if [ ! -z "$snapshotID" ];
  then
    cat temp.json | jq -c --arg snapshotID $snapshotID --argjson v $v '.[$v].status.providerSnapshotID |= $snapshotID' > volumesnapshots.json
    mv volumesnapshots.json temp.json
  fi
  ((v++))
done

mv temp.json $veleroBackupName-volumesnapshots.json

gzip $veleroBackupName-volumesnapshots.json

echo

#upload updated config to s3
output=$(aws s3 cp ./$veleroBackupName-volumesnapshots.json.gz s3://$veleroS3Bucket/backups/$veleroBackupName/$veleroBackupName-volumesnapshots.json.gz)

rm $veleroBackupName-volumesnapshots.json.gz

echo
echo "Snapshots of velero backup $veleroBackupName are restored. Please proceed with restore via velero CLI."
