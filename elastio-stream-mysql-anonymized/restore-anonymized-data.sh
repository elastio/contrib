#!/bin/bash

if [ -z $1 ] ; then
  echo "The recovery point ID is required" && exit 1;
fi

if [ -z $2 ] ; then
  echo "The recovery file name is required" && exit 2;
fi

RECOVERY_POINT=$1
RECOVERY_FILE_NAME=$2

elastio stream restore --rp ${RECOVERY_POINT} > ${RECOVERY_FILE_NAME}
