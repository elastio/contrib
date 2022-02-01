# Elastio AWS Fargate stream backup tutorial
> Before starting, please make sure aws-cliv2, and docker cli are installed.
1. Roles and polices.
    1. Create ECR polices:
        1. From AWS console, select IAM service, select `Policies` then 'Create Policy'.
        2. Under Service select `Elastic Container Registry`.
        3. Under Actions select `All Elastic Container Registry actions (ecr:*)`.
        4. Under Resources select `specific` and `Add ARN`. Here we will select the region, leave our account number and select Any for Repository name.
        5. Enter policy name 'ECR_FullAccess'.
    2. Roles
        1. From AWS console, select IAM service, select `Roles`.
        2. If you already have a role for ECS tasks you should add the following permissions: 
        ```AmazonECSTaskExecutionRolePolicy, SecretsManagerReadWrite, AmazonS3FullAccess, ECR_FullAccess, ElastioFullAdmin``` or create new role with these permissions.
            If you create new role do this steps:
            1. In the navigation pane, choose Roles, Create role.
            2. In the Select type of trusted entity section, choose AWS service, Elastic Container Service.
            3. For "Select your use case", choose the Elastic Container Service Task, then choose Next: Permissions.
            4. In the Attach permissions policies section, search for ```AmazonECSTaskExecutionRolePolicy, SecretsManagerReadWrite, AmazonS3FullAccess, ECR_FullAccess, ElastioFullAdmin``` select policies, and then choose Next: Tags.
            5. For Add tags (optional), specify custom tags to associate with the policy and then choose Next: Review.
            6. For Role name, type `ecs_task_execution_role` and choose Create role.
2. Build and push docker image:
    > if you use the arm64/amd64 architecture, use an instance with the same architecture that you used to build the image.
    > Before you start this section, review the dockerfile and read its comments. In the comments you will see the possible values for arguments such as ARCH(architecture), VERSION_TAG(elastio cli version)
    > You can find the latest version at this link. https://gallery.ecr.aws/elastio-dev/elastio-cli
    1. Edit file contrib/elastio-fargate-stream-backup/app/config_file.py and put data about s3 bucket and file what will backup.
    2. Register your docker cli by getting the ecr public image with the command:
        ```aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws```
        
    3. Open your ECR repository that we created earlier and press the option "View push commands".  The screen will list four commands. Run them in your terminal to build the docker image.
3. Create a Fargate Cluster.
    1. From AWS console, select `Elastic Container Service`, select `Create Cluster`.
    2. Under Select cluster template, select networking only.
    3. Enter your cluster name and press `Create`.
4. Create an ECS Task.
    
    1. Select `Task Definitions` from the left menu. Then select `Create new task definition`.
    2. Select Fargate.
    3. Select Next Step.
    4. Enter `Task definition name`.
    5. In the `Task role` field choose `ecs_task_execution_role`.
    6. Operating system family, choose `Linux`.
    7. Task execution role.
    8. Task memory (GB): 4GB
    9. Task CPU (vCPU): 1vCPU
    10. Select `Add container`.
    11. Enter container name.
    12. In the image field put URI of your docker image from ECR repository.  Copy the arn from the ECS tab.
    13. Set `Private repository authentication` to true
    14. Memory Limits (MiB):
        1. Soft limit: `4096`
        2. Hard limit: `4096`
    15. Press `Add`.
    16. Press `Create`.
5. Run the ECS schedule task.
    
    1. Select your cluster in ECS Clusters.
    2. In the navigation tabs choose `Scheduled Tasks`.
    3. Click `Create` button.
    4. Enter `Schedule rule name`.
    5. Enter `Target id`.
    6. Launch type choose `Fargate`.
    7. Task Definition, choose your task definition.
    8. Cluster VPC, select a vpc from the list. For our app, any will do.
    9. Add at least one subnet.
    10. Auto-assign public IP: ENABLED
    11. Press `Create` button.  This will run the task on the schedule that was selected.