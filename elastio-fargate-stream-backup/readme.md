# Elastio fargate stream backup

> Before starting, please check do you have aws-cliv2, and docker cli installed.

1. From AWS console, select IAM service, select `Users` if you already have user you could add permission `AmazonECS_FullAccess` or create new user and attach `AmazonECS_FullAccess` permission from the existing polices.

2. Create ECR polices:
    
    1. From AWS console, select IAM service, select `Policies` then 'Create Policy'.
    2. Under Service select `Elastic Container Registry`.
    3. Under Actions select `All Elastic Container Registry actions (ecr:*)`.
    4. Under Resources select `specific` and `Add ARN`. Here we will select the region, leave our account number and select Any for Repository name.

3. Attach the new policies to the IAM user:

    1. From AWS console, select IAM service, select `Users`, choice your user
    2. Select `Add permission`
    3. Select `Attach existing policies directly` in the search field enter name of ECR policy what was created earlier.

4. Build and push docker image:
    > if you want use arm64/amd64 architecture you should use the instance in the same architecture to building image

    > Before starting doing this paragraph look at dockerfile and read comments. In the comments you can see the possible values for arguments such as ARCH(architecture), VERSION_TAG(elastio cli version)

    1. Register your docker cli by getting the ecr public image with the command:
	"aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws"
	2. Open your ECR repository that we created earlier and press the option "View push commands". 
	If will show you 4 commands that you should run in your terminal that will build your docker image.

5. Create a Fargate Cluster.

    1. From AWS console, select `Elastic Container Service`, select `Create Cluster`.
    2. Under Select cluster template we are going to select networking only.
    3. Enter your claster name and press `Create`.

6. Create an ECS Task.
    
    1. Select `Task Definitions` from the left menu. Then select `Create new Task Definition`.
    2. Select Fargate.
    3. Select Next Step.
    4. Enter `Task definition name`.
    5. In the `Task role` field choice `ecsTaskExecutionRole`.
    6. Operating system family choice `Linux`.
    7. Task memory (GB): 4GB
    8. Task CPU (vCPU): 1vCPU
    9. Select `Add container`.
    10. Enter container name.
    11. To the image field put URI of your docker image from ECR repository
    12. Private repository authentication set true
    13. Memory Limits (MiB):
        1. Soft limit: `4096`
        2. Hard limit: `4096`
    14. Port mappings set `5000`.
    15. Press `Add`.
    16. Press `Create`.

7. Run the ECS Task.
    
    1. Select the task in the Task definition list.
    2. Click `Actions` and select `Run Task`.
    3. For `Launch type`: select `Fargate`.
    > Make sure Cluster: is set to the fargate-cluster we created earlier.
    4. Cluster VPC select a vpc from the list. For our app, any will do.
    5. Add at least one subnet.
    6. `Auto-assign public IP` should be set to ` ENBABLED`.
    7. Edit the security group.
    8. Press `Add rule`.
        1. Type: `Custom TCP`.
        2. Port range: `5000`.
    9. And finally, run the task by clicking `Run Task` in the lower left corner of the page.

Check to see if our app is running
After you run the Task, you will be forwarded to the `fargate-cluster` page. When the `Last Status` for your cluster changes to `RUNNING`, your app is up and running. You may have to refresh the table a couple of times before the status is `RUNNING`. This can take a few minutes.

### Test

1. Click on the link in the Task column.
2. Find the `Public IP` address in the Network section of the Task page.
3. And send to this address GET request with next parameters:
    ```
    {
		  "bucket_name": "<your-bucket-name>",
		  "file_key": "<file-key>",
		  "stream_name": "<elastio-stream-name>",
		  "vault_name": "<vault-name>"
	}
    ```

    Python example:
    ```
        import requests
        response = requests.get("http://3.17.185.66:5000", params={
            "bucket_name": "test1-storage-s3",
            "file_key": "Data8317.csv",
            "stream_name": "Data8317.csv",
            "vault_name": "default2"
            })

        response.text

        {
            "msg": "The file was streamed successfully.",
            "status": 200,
            "statusCommand": 0
        }
    ```
