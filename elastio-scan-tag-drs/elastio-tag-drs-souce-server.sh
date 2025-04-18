#!/bin/bash

echo
echo "Please select an option (1, 2, or 3):"
echo "1. Add Elastio scan tag (elastio:action=scan) to all DRS source servers to enable scanning."
echo "2. Add Elastio scan tag (elastio:action=scan) to specific DRS source servers to enable scanning."
echo "3. Remove Elastio scan tag from all DRS source servers."
echo
read -rp "Your choice: " choice

case $choice in
    1)
        echo
        echo "You selected option 1: Add Elastio scan tag to all DRS source servers."

        drs_source_servers=$(aws drs describe-source-servers --query "items[].{ARN:arn,ID:sourceServerID}" --output json 2>&1)

        if echo "$drs_source_servers" | grep -q "AccessDenied"; then
            echo "You don't have permission to manage DRS source servers."
            exit 1
        fi

        echo "$drs_source_servers" | jq -r '.[].ARN' | while read -r arn; do
            output=$(aws drs tag-resource --resource-arn "$arn" --tags elastio:action=scan 2>&1)
            if echo "$output" | grep -q "AccessDenied"; then
                echo "You don't have permission to tag DRS source server: $arn"
                exit 1
            fi
        done

        echo
        echo "Elastio scan tag added to the following servers:"
        echo "$drs_source_servers" | jq -r '.[].ID'
        ;;

    2)
        echo
        echo "You selected option 2: Add Elastio scan tag to specific DRS source servers."

        drs_source_servers=$(aws drs describe-source-servers --query "items[].{ARN:arn,ID:sourceServerID}" --output json 2>&1)

        if echo "$drs_source_servers" | grep -q "AccessDenied"; then
            echo "You don't have permission to manage DRS source servers."
            exit 1
        fi

        echo
        echo "The following source servers are located in the current region:"
        echo "$drs_source_servers" | jq -r '.[].ID'
        echo
        echo "Please provide a space-separated list of server IDs (e.g., s-140525080f1c32387 s-113fa2a65e3b82a81 s-1c92115b0575cdfc8)."
        read -rp "Provide a list of servers: " user_selected_ids

        echo
        echo "Elastio scan tag added to the following servers:"

        while IFS= read -r arn; do
            server_id="${arn##*/}"
            if [[ " $user_selected_ids " =~ " $server_id " ]]; then
                output=$(aws drs tag-resource --resource-arn "$arn" --tags elastio:action=scan 2>&1)
                if echo "$output" | grep -q "AccessDenied"; then
                    echo "You don't have permission to tag DRS source server: $server_id"
                    exit 1
                fi
                echo "$server_id"
            fi
        done <<< "$(echo "$drs_source_servers" | jq -r '.[].ARN')"
        ;;

    3)
        echo
        echo "You selected option 3: Remove Elastio scan tag from all DRS source servers."

        drs_source_servers=$(aws drs describe-source-servers --query "items[].{ARN:arn,ID:sourceServerID}" --output json 2>&1)

        if echo "$drs_source_servers" | grep -q "AccessDenied"; then
            echo "You don't have permission to manage DRS source servers."
            exit 1
        fi

        echo "$drs_source_servers" | jq -r '.[].ARN' | while read -r arn; do
            output=$(aws drs untag-resource --resource-arn "$arn" --tag-keys elastio:action 2>&1)
            if echo "$output" | grep -q "AccessDenied"; then
                echo "You don't have permission to untag DRS source server: $arn"
                exit 1
            fi
        done

        echo
        echo "Elastio scan tag removed from the following servers:"
        echo "$drs_source_servers" | jq -r '.[].ID'
        ;;

    *)
        echo "Invalid choice. Please run the script again and enter 1, 2, or 3."
        exit 1
        ;;
esac
