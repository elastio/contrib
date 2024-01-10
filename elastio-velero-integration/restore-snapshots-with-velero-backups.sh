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
  echo $(date)": Found snapshots with velero backup $veleroBackupName and namespace $namespaceName in AWS:"
  s=0
  for snapshotID in $(aws ec2 describe-snapshots --filters Name=tag:velero.io/backup,Values=$veleroBackupName Name=tag:kubernetes.io/created-for/pvc/namespace,Values=$namespaceName --query "Snapshots[].SnapshotId" --output text)
  do
    ((s++))
    echo $s. $snapshotID
	var=$(aws ec2 delete-tags --resources $snapshotID --tags Key=elastio:imported-to-rp 2>&1)
	var=$(aws ec2 create-tags --resources $snapshotID --tags Key=elastio:velero,Value=true 2>&1)
  done
fi

#get RPs by namespace and velero backup name
RPs=($(elastio rp list --limit 1000 --tag velero.io/backup=$veleroBackupName | grep namespace=$namespaceName | grep -oP rp-[A-Za-z0-9]+))
if [ ! -z "$RPs" ];
then
  echo
  echo $(date)": Found elastio recovery points with velero backup $veleroBackupName and namespace $namespaceName:"
  r=0
  for RP in ${RPs[*]}
  do
    ((r++))
    echo $r. $RP
  done
fi

#download velero config file from s3
var=$(aws s3 cp s3://$veleroS3Bucket/backups/$veleroBackupName/$veleroBackupName-volumesnapshots.json.gz ./temp.json.gz 2>&1)

#upload a backup of config to s3
var=$(aws s3 cp ./temp.json.gz s3://$veleroS3Bucket/backups/$veleroBackupName/$veleroBackupName-volumesnapshots-original-$(date +%s).json.gz 2>&1)

gzip -d temp.json.gz

echo
echo $(date)": Working with snashots list of the $veleroBackupName velero backup."
echo

for backup in $(cat temp.json  | jq .[] -c)
do
  echo -ne "."
  #for each volume in the velero backup get volume and snapshot ids
  snapshot=$(echo $backup | jq .status.providerSnapshotID -r)
  volume=$(echo $backup | jq .spec.providerVolumeID -r)
  if [ "$snapshot" != "null" ]
  then
    #check if snapshot is still present in the aws
    snapshotinaws=$(aws ec2 describe-snapshots --snapshot-ids $snapshot --query "Snapshots[].SnapshotId" --output text 2>/dev/null)
    #if snapshot not present in aws check elastio rps
    if [ -z "$snapshotinaws" ];
    then
      elastiorp=$(elastio rp list --ebs $volume --tag velero.io/backup=$veleroBackupName 2>/dev/null)
      if [ -z "$elastiorp" ];
      then
        echo "ERROR: elastio recovery point of snapshot $snapshot for velero backup $veleroBackupName is missing. This might affect velero restore."
      fi
      if [ ! -z "$elastiorp" ];
      then
        elastiorpid=$(echo $elastiorp | grep -oP rp-[A-Za-z0-9]+)
        nanesmace=$(echo $elastiorp | grep -oP $namespaceName)
        #if elastio rp has a tag with given namespace start restore
        if [ "$nanesmace" = "$namespaceName" ]
    	then
    	  var=$(elastio ebs restore --rp $elastiorpid --restore-asset-tags --restore-snapshots --tag elastio:velero=true 2>&1)
    	fi
      fi
    fi
  fi
  #some backups has failed snapshot status, nothing we can do here
  if [ "$snapshot" = "null" ]
  then
    echo "Velero backup $veleroBackupName is missing snapshot for volume $volume. This might affect velero restore."
  fi
done

sleep 30

if [ "$(elastio job list --output-format json --kind restore)" != "[]" ];
then
echo
echo
echo $(date)": EBS restore is in progress, the duration will depend on the data size."
echo
fi

#wait restore to finish
while [[ $(elastio job list --output-format json --kind restore) != "[]" ]]
do
  sleep 30
  echo -ne "."
done

echo
echo $(date)": Snapshot(s) available for the velero restore:"
s=0
for snapshotID in $(aws ec2 describe-snapshots --filters Name=tag:velero.io/backup,Values=$veleroBackupName Name=tag:kubernetes.io/created-for/pvc/namespace,Values=$namespaceName Name=tag:elastio:velero,Values=true --query "Snapshots[].SnapshotId" --output text)
do
  ((s++))
  echo $s. $snapshotID
done

echo
echo $(date)": Updating Velero configuration file."
echo

#replace snapshot IDs with new values
declare -i v=0

for volumeID in $(cat temp.json | jq .[].spec.providerVolumeID -r)
do
  snapshotID=$(aws ec2 describe-snapshots --filters Name=tag:elastio:restored-from-asset,Values=$volumeID Name=tag:velero.io/backup,Values=$veleroBackupName Name=tag:kubernetes.io/created-for/pvc/namespace,Values=$namespaceName Name=tag:elastio:velero,Values=true --query "Snapshots[].SnapshotId" --output text)
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
echo $(date)": Snapshots of velero backup $veleroBackupName are restored. Please proceed with restore via velero CLI."
echo
