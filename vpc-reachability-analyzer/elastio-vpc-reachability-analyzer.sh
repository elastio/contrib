ami=$(aws ec2 describe-images --owners amazon --filters "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-jammy*" --query 'sort_by(Images, &CreationDate)[0].ImageId' --output text)

for vpcID in $(aws ec2 describe-vpcs --query "Vpcs[].VpcId" --output text)
do
  echo
  echo "$vpcID:"
  for subnetID in $(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$vpcID" --query "Subnets[*].SubnetId" --output text)
    do
	  instanceID=$(aws ec2 run-instances --image-id $ami --instance-type t2.nano --subnet-id $subnetID \
	    --associate-public-ip-address --query "Instances[].InstanceId" --output text --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=elastio-reachability-analyzer}]')
	  
	  while [[ $(aws ec2 describe-instances --instance-ids $instanceID --query "Reservations[].Instances[].State.Name" --output text) != "running" ]]
	  do
	    sleep 5
	  done
	  
	  pathID=$(aws ec2 create-network-insights-path --source $instanceID --protocol TCP --filter-at-source '{"DestinationAddress": "8.8.8.8"}' \
	    --query "NetworkInsightsPath.NetworkInsightsPathId" --output text)
	  
	  analysisID=$(aws ec2 start-network-insights-analysis --network-insights-path-id $pathID --query "NetworkInsightsAnalysis.NetworkInsightsAnalysisId" --output text)
	  
	  while [[ $(aws ec2 describe-network-insights-analyses --network-insights-analysis-ids $analysisID --query "NetworkInsightsAnalyses[].Status" --output text) != "succeeded" ]]
	  do
	    sleep 5
	  done
	  
	  analysisResult=$(aws ec2 describe-network-insights-analyses --network-insights-analysis-ids $analysisID --query "NetworkInsightsAnalyses[].NetworkPathFound" --output text)
	  
	  output=$(aws ec2 delete-network-insights-analysis --network-insights-analysis-id $analysisID)
	  
	  output=$(aws ec2 delete-network-insights-path --network-insights-path-id $pathID)
	  
	  output=$(aws ec2 terminate-instances --instance-ids $instanceID)
	  
	  echo " - $subnetID - Reachable: $analysisResult"
	  echo
	done
done
