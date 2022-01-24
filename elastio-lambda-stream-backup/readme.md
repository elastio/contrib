# Elastio lambda stream backup

> Before starting, please check do you have aws-cliv2, and docker cli installed.

1. From AWS console, select IAM, select Roles then create IAM role with "ElastioLocalBackup".

2. From the AWS console, select ECR and create an ECR repository for storing your docker image.

3. Unpack archive and go into unpacked folder.

> if you want use arm64/amd64 architecture you should use the instance in the same architecture to building image

4. Build and push docker image:
	> Before starting doing this paragraph look at dockerfile and read comments
	> In the comments you can see the possible values for arguments such as ARCH(architecture), VERSION_TAG(elastio cli version)
	1. Register your docker cli by getting the ecr public image with the command:
	"aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws"
	2. Open your ECR repository that we created earlier and press the option "View push commands". 
	If will show you 4 commands that you should run in your terminal that will build your docker image.

5. Create a Lambda function:
	1. Go to your AWS console and select the Lambda service, select Create Function, then select "Container image".
	2. Enter function name
	3. Press button "Browse images" and choose the repository and version of image that you created in section
	4. In the Permission paragraph press "Change default execution role" and choose the option "Use an existing role" and
	in the field below enter the name of the role that we created earlier in the section 1.
	5. Press "Create function"

6. Edit Lambda function configuration:
	1. Open "Configuration" tab
	2. In paragraph "Execution role" press "Edit"
	3. In field "Memory" you should set value "10240"
	4. In field "Timeout" you should set up time to 15 min.
	5. Press "Save"

7. Test Lambda
	1. Open "Test" tab
	2. Put the same json in test field
	```
		{
		  "bucket_name": "<your-bucket-name>",
		  "file_key": "<file-key>",
		  "stream_name": "<elastio-stream-name>",
		  "vault_name": "<vault-name>"
		}
	```
	
	Example:

	```
	{
	  "bucket_name": "cf-templates-eju7784j6dl0-us-east-2",
	  "file_key": "dmesg.log",
	  "stream_name": "elastio-lambda-stream-test",
	  "vault_name": "default"
	}
	```

7.3 Press "Test"
