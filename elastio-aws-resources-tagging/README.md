In certain AWS accounts, custom tags are necessary for resource management. To streamline and automate this process, we have designed a script for tagging elastio AWS resources.

## Requirements
Please ensure that you have the following prerequisites in place:
 - Linux box with the AWS Command Line Interface (CLI) and the jq tool installed. 
 - Ensure that you have established connection to the AWS account where elastio is currently running.

OR

Alternatively, you can use a cloud shell console directly within the AWS account where elastio is operational. 

### Usage

To download the script, run the following command:
```
curl https://raw.githubusercontent.com/elastio/contrib/master/elastio-aws-resources-tagging/tag-elastio-resources.sh -o tag-elastio-resources.sh
```

Next, make the file executable by running:
```
chmod +x tag-elastio-resources.sh
```

Finally, execute the script with the desired tags:
```
./tag-elastio-resources.sh -t tag1=value1 -t tag2=value2
```

As a result, all Auto Scaling groups and Launch templates owned by elastio will be tagged with the appropriate tags.
