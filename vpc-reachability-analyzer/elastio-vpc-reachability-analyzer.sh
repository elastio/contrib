#!/bin/bash
set -o errexit
set -o nounset

vpcIDs=()
v=1
vpcs=($(aws ec2 describe-vpcs --query 'Vpcs[].[VpcId,IsDefault,Tags[?Key==`Name`].Value]' --output text))

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
for subnetID in $(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$vpcID" --query "Subnets[*].SubnetId" --output text)
do
  echo "Testing ${subnetID} in ${vpcID} by launching a test t2.micro EC2 instance..."
  instanceID=$(aws ec2 run-instances \
    --image-id resolve:ssm:/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64 \
    --instance-type t2.micro \
    --subnet-id $subnetID \
    --query "Instances[].InstanceId" \
    --output text \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=elastio-reachability-analyzer}]')

  while [[ $(aws ec2 describe-instances --instance-ids $instanceID --query "Reservations[].Instances[].State.Name" --output text) != "running" ]]
  do
    echo "Waiting for ${instanceID} to start..."
    sleep 5
  done

  echo "Test instance ${instanceID} is running; evaluating reachability..."

  pathID=$(aws ec2 create-network-insights-path --source $instanceID --protocol TCP --filter-at-source '{"DestinationAddress": "8.8.8.8"}' \
    --query "NetworkInsightsPath.NetworkInsightsPathId" --output text)

  analysisID=$(aws ec2 start-network-insights-analysis --network-insights-path-id $pathID --query "NetworkInsightsAnalysis.NetworkInsightsAnalysisId" --output text)

  while [[ $(aws ec2 describe-network-insights-analyses --network-insights-analysis-ids $analysisID --query "NetworkInsightsAnalyses[].Status" --output text) != "succeeded" ]]
  do
    echo "Waiting for reachability analysis ${analysisID} to complete..."
    sleep 5
  done

  analysisResult=$(aws ec2 describe-network-insights-analyses --network-insights-analysis-ids $analysisID --query "NetworkInsightsAnalyses[].NetworkPathFound" --output text)

  echo "Cleaning up reachability analysis"
  output=$(aws ec2 delete-network-insights-analysis --network-insights-analysis-id $analysisID)

  output=$(aws ec2 delete-network-insights-path --network-insights-path-id $pathID)

  echo "Terminating test instance ${instanceID}..."
  output=$(aws ec2 terminate-instances --instance-ids $instanceID)

  IPv4=$(aws ec2 describe-subnets --subnet-ids $subnetID --query "Subnets[].MapPublicIpOnLaunch" --output text)

  echo " - $subnetID - Auto-assign public IPv4: $IPv4; Internet reachable: $analysisResult"
done
