#!/bin/bash

source .env

if [ -z $1 ] ; then
  echo "The Oracle database name is required" && exit 1;
fi

if [ -z $2 ] ; then
  echo "The AWS S3 bucket is required" && exit 2;
fi

if [ -z $3 ] ; then
  echo "The Oracle table is required" && exit 3;
fi

# The following ARGS must be passed from the command line
DATABASE=$1
S3_BUCKET=$2
TABLE=$3

TODAY=$(date +'%Y-%m-%d')
STRING=$(echo $RANDOM | md5sum | head -c 5; echo;)

DUMPFILE="${TABLE}-${TODAY}-${STRING}.dmp"
LOGFILE="${TABLE}-${TODAY}-${STRING}.log"

echo "================================================="
echo "Exporting Oracle data..."
echo "================================================="
echo ""

OUTPUT=$(/usr/lib/oracle/21/client64/bin/expdp ${USERNAME}/${PASSWORD}@${HOST}:1521/${DATABASE} DIRECTORY=DATA_PUMP_DIR tables=${TABLE} DUMPFILE=${DUMPFILE} LOGFILE=${LOGFILE})

QUERY="SELECT rdsadmin.rdsadmin_s3_tasks.upload_to_s3(p_bucket_name => '${S3_BUCKET}', p_prefix => '', p_s3_prefix => '', p_directory_name => 'DATA_PUMP_DIR') AS TASK_ID FROM DUAL;"

OUTPUT=$(echo "${QUERY}" | sqlplus -s ${USERNAME}/${PASSWORD}@${HOST}:1521/${DATABASE})

echo "================================================="
echo "Sleeping for 30 seconds for I/O to complete..."
echo "================================================="
echo ""
sleep 30

echo "================================================="
echo "Backing up S3 to Elastio"
echo "================================================="
echo ""
OUTPUT=$(aws s3 cp s3://${S3_BUCKET}/${DUMPFILE} - | elastio stream backup --stream-name ${DUMPFILE})
OUTPUT=$(aws s3 cp s3://${S3_BUCKET}/${LOGFILE} - | elastio stream backup --stream-name ${LOGFILE})

echo "================================================="
echo "Done"
echo "================================================="
echo ""

