#!/bin/bash
set -o errexit
set -o nounset

paragraph=$(cat <<'EOP'
This script automates the process of evaluating the subnets within a VPC to
test if they have the necessary access to be used with Elastio.

To use it, choose the VPC you want to evaluate from the list, and the script
will test each subnet in that VPC, one by one, by performing a Network
Reachability Analyzer analysis.

NOTE: This script will launch one very short-lived t2.micro instance in each
subnet of the VPC, and it will perform Network Reachability Analyzer analysis,
both of which incurr AWS charges. These charges are very small, but they will
be incurred.

Please also note that this script only works within the AWS environment and
requires appropriate permissions to create and manage EC2 instances and network
paths. Ensure you have these permissions before running the script to avoid
execution errors.

EOP
)

# Use 'fmt' to wrap the text to the current terminal width
# Fall back to regular echo if that's not available
echo "$paragraph" | fmt -w "$(tput cols)" || echo "${paragraph}"

# Try to use AWS_REGION if it's set
if [ -n "${AWS_REGION+x}" ]; then
  region="$AWS_REGION"
# If not, use AWS_DEFAULT_REGION
elif [ -n "${AWS_DEFAULT_REGION+x}" ]; then
  region="$AWS_DEFAULT_REGION"
# If neither is set, use the default region from aws configure
else
  region=$(aws configure get region 2>/dev/null)
  # If aws configure does not return a region, exit with an error
  if [ -z "$region" ]; then
    echo "AWS region is not set; set the AWS_REGION or AWS_DEFAULT_REGION env var or configure one with `aws configure`" >&2
    exit 1
  fi
fi

echo
echo "Discovering available VPCs in ${region}..."

vpcIDs=()
v=1
vpcs=($(aws ec2 describe-vpcs --query 'Vpcs[].[VpcId,IsDefault,Tags[?Key==`Name`].Value]' --output text))
subnet_info=() # Array to store subnet details

if [ -z "$vpcs" ];
then
  echo
  echo "Could not find any VPCs."
  echo
  exit
fi

echo
for ((i = 0 ; i < ${#vpcs[@]} ; i+=3)); do
  vpc_id=${vpcs[$i]}
  is_default=${vpcs[$i+1]}
  name_tag=${vpcs[$i+2]}

  echo "$v: ${vpc_id} (Name: ${name_tag}, IsDefault: ${is_default})"
  vpcIDs+=(${vpcs[$i]})
  ((v++))
done

echo
read -p "Select VPC (Press Enter to select VPC 1, or Ctrl-D to abort): " vpc

if [ -z "$vpc" ];
then
   vpc=1
fi

if [ $vpc -gt ${#vpcIDs[@]} ]
then
  echo "$vpc isn't a valid VPC number."
  exit
fi

vpcID=${vpcIDs[$vpc-1]}

echo
echo "Analysing $vpcID:"
subnets_ids=($(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$vpcID" --query "Subnets[*].SubnetId" --output text))

for subnetID in "${subnets_ids[@]}"
do
  name_tag=$(aws ec2 describe-subnets --subnet-ids "$subnetID" --query "Subnets[].Tags[?Key=='Name'].Value" --output text)
  if [ -z "$name_tag" ]
  then
    subnet_display_name="${subnetID}"
  else
    subnet_display_name="${subnetID} (${name_tag})"
  fi

  echo "Testing ${subnet_display_name} in ${vpcID} by launching a test t2.micro EC2 instance..."

  IPv4=$(aws ec2 describe-subnets --subnet-ids $subnetID --query "Subnets[].MapPublicIpOnLaunch" --output text)
  instanceID=$(aws ec2 run-instances \
    --image-id resolve:ssm:/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64 \
    --instance-type t2.micro \
    --subnet-id $subnetID \
    --query "Instances[].InstanceId" \
    --output text \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=elastio-vpc-reachability-test}]')

  while [[ $(aws ec2 describe-instances --instance-ids $instanceID --query "Reservations[].Instances[].State.Name" --output text) != "running" ]]
  do
    echo "  Waiting for ${instanceID} to start..."
    sleep 5
  done

  echo "  Test instance ${instanceID} is running; evaluating reachability..."

  pathID=$(aws ec2 create-network-insights-path --source $instanceID --protocol TCP --filter-at-source '{"DestinationAddress": "8.8.8.8"}' \
    --query "NetworkInsightsPath.NetworkInsightsPathId" --output text)

  analysisID=$(aws ec2 start-network-insights-analysis --network-insights-path-id $pathID --query "NetworkInsightsAnalysis.NetworkInsightsAnalysisId" --output text)

  while [[ $(aws ec2 describe-network-insights-analyses --network-insights-analysis-ids $analysisID --query "NetworkInsightsAnalyses[].Status" --output text) != "succeeded" ]]
  do
    echo "  Waiting for reachability analysis ${analysisID} to complete..."
    sleep 5
  done

  analysisResult=$(aws ec2 describe-network-insights-analyses --network-insights-analysis-ids $analysisID --query "NetworkInsightsAnalyses[].NetworkPathFound" --output text)

  echo "  Cleaning up reachability analysis"
  output=$(aws ec2 delete-network-insights-analysis --network-insights-analysis-id $analysisID)

  output=$(aws ec2 delete-network-insights-path --network-insights-path-id $pathID)

  echo "  Terminating test instance ${instanceID}..."
  output=$(aws ec2 terminate-instances --instance-ids $instanceID)

  echo "  ${subnet_display_name} reachability analysis: $analysisResult"
  echo

  # Store the subnet details
  subnet_info+=("${subnet_display_name} - Auto-assign public IPv4: $IPv4; Internet reachable: $analysisResult")
done

echo
echo "Subnet Analysis Results:"
echo "(Subnets with a value of 'True' for Internet reachability can be used with Elastio)"

for info in "${subnet_info[@]}"; do
  echo "  $info"
done
