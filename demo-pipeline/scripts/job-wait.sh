#!/bin/bash

JOB_ID=${1}

echo "Waiting for job id ${JOB_ID}"

while true; do
  OUTPUT=$(elastio job output --job-id ${JOB_ID} --output-format json)
  echo "[$(date -Isec|tr -d "\n")] ${OUTPUT}"
  if [ "$(echo "${OUTPUT}" | jq -r .error)" == "null" ]; then
    echo "${MSG}"
    if [ "$(echo "${OUTPUT}" | jq -r .status)" != "Succeeded" ]; then
      exit 255
    else
      echo ${OUTPUT} | jq -r '.data.rp_id' > rp_id
      exit 0
    fi
  fi
  sleep $(( RANDOM % 15 ))
done
