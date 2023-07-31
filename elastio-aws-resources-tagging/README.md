This article guides on utilizing the script for AWS ASG and Launch Template tagging. 
In certain AWS accounts, custom tags are necessary for resource management. To streamline and automate this process, we have designed a script for tagging elastio AWS resources.

## Requirements
Please ensure that you have the following prerequisites in place:
 - Linux box with the AWS Command Line Interface (CLI) and the jq tool installed. 
 - Ensure that you have established connection to the AWS account where elastio is currently running.

OR

Alternatively, you can use a cloud shell console directly within the AWS account where elastio is operational. 

### Script usage

Create a new `script.sh` file and copy the content of the script to the file.

Replace keys and values with your desired custom tags:

```
tags='{"Tags":[{"Key": "name1","Value": "value2"},{"Key": "name2","Value": "value2"}]}'
```

If you need only one tag, remove the second element of the array, like in the example:

```
tags='{"Tags":[{"Key": "name1","Value": "value2"}]}'
```

Run `chmod +x script.sh` command to make file executable.

Run the script `./script.sh`.

As a result, all ASGs and Launch templates which elastio owns will be tagged with appropriate tags.


### Script
```
tags='{"Tags":[{"Key": "name1","Value": "value2"},{"Key": "name2","Value": "value2"}]}'


###add custom tags to ASGs

customTagsASG=""

for element in $(echo $tags | jq ".Tags[]" -c)
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
  for element in $(echo $tags | jq ".Tags[]" -c)
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
```