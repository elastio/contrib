#!/bin/bash

#usage info
usage(){
  echo "Usage:"
  echo "  $0 -t tag"
  echo
  echo "Example:"
  echo "  $0 -t tag1=value1 -t tag2=value2"
  echo
  exit
}

#parse options and arguments
while getopts "t:" option; do
  case $option in
    "t")
      arguments+=($(echo '{"Key":"'${OPTARG%=*}'","Value":"'${OPTARG#*=}'"}'))
      ;;
    *)
      usage
      ;;
  esac
done

#no options were provided or there was a mistake
if [ "$OPTIND" -eq "1" ] || [ "$OPTIND" -le "$#" ]; then
  usage
fi


###add custom tags to ASGs

customTagsASG=""

for element in "${arguments[@]}"
do

 customTag=$(echo "Key=$(echo $element | jq ".Key" -r),Value=$(echo $element | jq ".Value" -r)")

 #iterate through ASG with elastio in name
 for ASGID in $(aws autoscaling describe-auto-scaling-groups --query "AutoScalingGroups[*].AutoScalingGroupName" --output text) ; \
 do

  if [[ "$ASGID" == *"elastio"* ]]; then

   customTagsASG+=$(echo "ResourceId=$ASGID,ResourceType=auto-scaling-group,$customTag,PropagateAtLaunch=false ")

  fi

 done

done

var=$(aws autoscaling create-or-update-tags --tags $customTagsASG)


###add custom tags to launchTemplates

#iterate through launchTemplates with elastio in tags
for launchTemplateName in $(aws ec2 describe-launch-templates --query "LaunchTemplates[*].LaunchTemplateName" --output text)
do

 #get launchTemplates tags
 launchTemplateData=$(aws ec2 describe-launch-template-versions --launch-template-name $launchTemplateName --versions $Default --query "LaunchTemplateVersions[0].LaunchTemplateData.{TagSpecifications:TagSpecifications}")

 if [[ "$launchTemplateData" == *"elastio"* ]]; then 

  #add custom tags to the existent array
  for element in "${arguments[@]}"
  do

   launchTemplateData=$(echo $launchTemplateData | jq ".TagSpecifications[0].Tags[.TagSpecifications[0].Tags | length] |= .+ $element" -c)
   launchTemplateData=$(echo $launchTemplateData | jq ".TagSpecifications[1].Tags[.TagSpecifications[1].Tags | length] |= .+ $element" -c)

  done

  #create new launchTemplate version with custom tags
  var=$(aws ec2 create-launch-template-version --launch-template-name $launchTemplateName --launch-template-data $(echo $launchTemplateData | jq "." -c))

  #make new launchTemplate version default
  var=$(aws ec2 modify-launch-template --launch-template-name $launchTemplateName --default-version \
  $(aws ec2 describe-launch-templates --launch-template-name $launchTemplateName --query "LaunchTemplates[].LatestVersionNumber" --output text))

 fi

done