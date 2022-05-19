#!/bin/bash

if [ -z $1 ] ; then
  echo "The database name is required" && exit 1;
fi

if [ -z $2 ] ; then
  echo "The recovery file name is required" && exit 2;
fi

DATABASE=$1
RECOVERY_FILE_NAME=$2

mysqldump ${DATABASE} | /home/ubuntu/myanon/myanon-main/main/myanon -f /home/ubuntu/elastio_mysql/elastio.cnf | elastio stream backup --stream-name ${RECOVERY_FILE_NAME}
