#!/bin/bash

#get elastio daily costs by usage type
aws ce get-cost-and-usage --output json --time-period Start=2024-04-28,End=2024-04-29 \
--metrics "UnblendedCost" "UsageQuantity" --granularity DAILY --group-by Type=DIMENSION,Key=USAGE_TYPE \
--filter '{ "Tags": { "Key": "elastio:resource", "Values": ["true"] } }' > elastio-usage-daily-cost-2024-04-28.json

aws ce get-cost-and-usage --output json --time-period Start=2024-04-17,End=2024-04-18 \
--metrics "UnblendedCost" "UsageQuantity" --granularity DAILY --group-by Type=DIMENSION,Key=USAGE_TYPE \
--filter '{ "Tags": { "Key": "elastio:resource", "Values": ["true"] } }' > elastio-usage-daily-cost-2024-04-17.json

aws ce get-cost-and-usage --output json --time-period Start=2024-04-22,End=2024-04-28 \
--metrics "UnblendedCost" "UsageQuantity" --granularity DAILY --group-by Type=DIMENSION,Key=USAGE_TYPE \
--filter '{ "Tags": { "Key": "elastio:resource", "Values": ["true"] } }' > elastio-usage-weekly-cost-2024-04-22-28.json

#get elastio daily costs by component tag
aws ce get-cost-and-usage --output json --time-period Start=2024-04-28,End=2024-04-29 \
--metrics "UnblendedCost" "UsageQuantity" --granularity DAILY --group-by Type=TAG,Key=elastio:component \
--filter '{ "Tags": { "Key": "elastio:resource", "Values": ["true"] } }' > elastio-tag-daily-cost-2024-04-28.json

aws ce get-cost-and-usage --output json --time-period Start=2024-04-28,End=2024-04-29 \
--metrics "UnblendedCost" "UsageQuantity" --granularity DAILY --group-by Type=DIMENSION,Key=USAGE_TYPE > elastio-all-usage-daily-cost-2024-04-28.json

zip -r elastio-costs.zip ./elastio*
