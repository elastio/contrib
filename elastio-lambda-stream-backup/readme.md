# Elastio Docker lambda stream backup

> Before starting, please check do you have aws-cliv2, and docker cli installed.

1. From AWS console, select IAM, select Roles then create IAM role with "ElastioFullAdmin".

2. From the AWS console, select ECR and create an ECR repository for storing your docker image.

3. Download code from contrib repository and open directory elastio-lambda-stream-backup.

> if you want to use arm64/amd64 architecture, you should use the coresponding architecture for the instance

4. Build and push docker image:
	1. Review the dockerfile and read the following comments for arguments such as ARCH(architecture), VERSION_TAG(elastio cli version)
	2. Register your docker cli by getting the ECR public image with the command:
	"aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws"
	3. Open your ECR repository you created earlier and press the button "View push commands". 
	You will see 4 commands you should run in your terminal to build your docker image.

5. Create a Lambda function:
	1. Go to your AWS console and select the Lambda service, select Create Function, then select "Container image".
	2. Enter a function name.
	3. Press the button "Browse images" and choose the repository and version of the image that you created in ECR.
	4. In the Permission paragraph press "Change default execution role" and choose the option "Use an existing role". In the field below enter the name of the role you created on step 1.
	5. Press "Create function".

6. Edit Lambda function configuration:
	1. Open "Configuration" tab.
	2. In paragraph "Execution role" press "Edit".
	3. In field "Memory" set value "10240".
	4. In field "Timeout" set time up to 15 min.
	5. Press "Save".

7. Run Lambda to perform stream backup with Elastio:
	1. Open "Test" tab.
	2. Insert the json with a similar strucrute in test field:
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

	3. Press "Test"
