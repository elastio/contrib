#!/bin/bash

set -euo pipefail

# -------------------------------
# Input parameters 
# -------------------------------
API_USER=""
API_PASS=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --user)
      API_USER="$2"
      shift 2
      ;;
    --pass)
      API_PASS="$2"
      shift 2
      ;;
    *)
      echo "Unknown parameter: $1"
      exit 1
      ;;
  esac
done

if [ -z "${API_USER:-}" ] || [ -z "${API_PASS:-}" ]; then
  echo "ERROR: --user and --pass are required"
  echo ""
  echo "Usage:"
  echo "  $0 --user <api_user> --pass <api_pass>"
  exit 1
fi

# -------------------------------
# Install dependencies
# -------------------------------
echo "Installing dependencies (jq, curl, unzip, AWS CLI)..."
sudo apt update -qq
sudo apt install -y -qq jq curl unzip
curl -sSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip -o awscliv2.zip >/dev/null
sudo ./aws/install >/dev/null

# -------------------------------
# Check AWS CLI access
# -------------------------------
if ! aws sts get-caller-identity >/dev/null 2>&1; then
  echo "ERROR: AWS CLI is not configured or has no access"
  exit 1
fi

# -------------------------------
# Get all relevant volumes
# Filter:
#  - non-root volumes only
#  - NTFS only
# -------------------------------
echo ""

VOLUMES_JSON=$(aws fsx describe-volumes \
  --query 'Volumes[?OntapConfiguration.StorageVirtualMachineRoot==`false` && OntapConfiguration.SecurityStyle==`NTFS`].{fs:FileSystemId,volume:VolumeId,path:OntapConfiguration.JunctionPath}' \
  --output json)

if [ "$(echo "$VOLUMES_JSON" | jq 'length')" -eq 0 ]; then
  echo "No matching volumes found"
  echo '[{"user":"","password":""}]' | jq '.'
  exit 0
fi

FS_IDS=$(echo "$VOLUMES_JSON" | jq -r '.[].fs' | sort -u)

RESULT='[{"user":"","password":""}]'

# -------------------------------
# Process each FSx
# -------------------------------
for FSID in $FS_IDS; do
  echo "Processing FSx: $FSID"

  # -------------------------------
  # Get management endpoint IP
  # -------------------------------
  MGMT_IP=$(aws fsx describe-file-systems \
    --file-system-ids "$FSID" \
    --query 'FileSystems[0].OntapConfiguration.Endpoints.Management.IpAddresses[0]' \
    --output text 2>/dev/null || true)

  if [ -z "${MGMT_IP:-}" ] || [ "$MGMT_IP" = "None" ]; then
    echo "WARNING: No management IP found for $FSID, skipping"
    continue
  fi

  echo ""

  # -------------------------------
  # Get share list
  # -------------------------------
  SHARE_LIST=$(curl -sk -u "$API_USER:$API_PASS" \
    "https://${MGMT_IP}/api/protocols/cifs/shares?return_records=true" 2>/dev/null || true)

  if [ -z "${SHARE_LIST:-}" ]; then
    echo "WARNING: ONTAP API returned no data for $FSID, skipping"
    continue
  fi

  if ! echo "$SHARE_LIST" | jq . >/dev/null 2>&1; then
    echo "WARNING: ONTAP API returned invalid JSON for $FSID, skipping"
    continue
  fi

  SHARE_COUNT=$(echo "$SHARE_LIST" | jq '.records | length // 0')

  if [ "$SHARE_COUNT" -eq 0 ]; then
    echo "INFO: No shares found for $FSID"
    continue
  fi

  # -------------------------------
  # Get detailed info for each share
  # -------------------------------
  SHARE_DETAILS=$(
    echo "$SHARE_LIST" \
      | jq -r '.records[]._links.self.href // empty' \
      | while read -r href; do
          [ -n "$href" ] || continue
          DETAIL=$(curl -sk -u "$API_USER:$API_PASS" "https://${MGMT_IP}${href}" 2>/dev/null || true)
          if [ -n "${DETAIL:-}" ] && echo "$DETAIL" | jq . >/dev/null 2>&1; then
            echo "$DETAIL"
          fi
        done \
      | jq -s '.'
  )

  if [ "$(echo "$SHARE_DETAILS" | jq 'length')" -eq 0 ]; then
    echo "INFO: No share details returned for $FSID"
    continue
  fi

  # -------------------------------
  # Match shares to volumes
  # -------------------------------
  MATCHED=$(jq -n \
    --arg fsid "$FSID" \
    --argjson vols "$VOLUMES_JSON" \
    --argjson shares "$SHARE_DETAILS" '
    [
      $shares[]
      | select(.name != null and .path != null)
      | select(.name != "c$" and .name != "ipc$")
      | {share: .name, path: .path} as $s
      | $vols[]
      | select(.fs == $fsid)
      | select(.path == $s.path)
      | {volume: .volume, share: $s.share}
    ]
  ')

  if [ "$(echo "$MATCHED" | jq 'length')" -eq 0 ]; then
    echo "INFO: No matching shares found for $FSID"
    continue
  fi

  # -------------------------------
  # Append matched entries to final result
  # -------------------------------
  RESULT=$(echo "$RESULT $MATCHED" | jq -s 'add')
done

# -------------------------------
# Final output
# -------------------------------
echo "Final result:"
echo "$RESULT" | jq '.'
