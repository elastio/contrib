In certain AWS accounts, custom tags are necessary for resource management. To streamline and automate this process, we have designed a script for tagging elastio AWS resources.

## Requirements
Please ensure that you have the following prerequisites in place:
 - Linux box with the AWS Command Line Interface (CLI) and the jq tool installed. 
 - Ensure that you have established connection to the AWS account where elastio is currently running.

OR

Alternatively, you can use a cloud shell console directly within the AWS account where elastio is operational. 

### Script usage

Create a new `script.sh` file and copy the content of the script to the file.

Run `chmod +x script.sh` command to make file executable.

Run the script `./script.sh -t tag1=value1 -t tag2=value2`.

As a result, all Auto Scaling groups and Launch templates which elastio owns will be tagged with appropriate tags.
