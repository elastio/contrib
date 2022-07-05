# Elastio EC2 backup ECS stopped task
1. Create ECR polices:
    1. From AWS console, select "IAM service" =>`Policies` =>'Create Policy'.
    2. Under the **Service** tab select `Elastic Container Registry`.
    3. Under the **Actions** tab select `All Elastic Container Registry actions (ecr:*)`.
    4. Under the **Resources** tab select `specific` =>`Add ARN`. Then choose the region, leave your account number and select "Any" for the Repository name.
    5. Enter 'ECR_FullAccess' as a policy name.

2. Roles
    1. From AWS console, select IAM service =>`Roles`.
    2. If you already have a role for ECS tasks, add the following permissions: 
    ```AmazonECSTaskExecutionRolePolicy, SecretsManagerReadWrite, AmazonECS_FullAccess, ECR_FullAccess, ElastioFullAdmin``` or create a new role with these permissions.
        
        Creating a new role follow these steps:
        1. In the navigation pane, choose "Roles" =>"Create role".
        2. In the "Select type of trusted entity section", choose "AWS service" => "Elastic Container Service".
        3. In "Select your use case", select the "Elastic Container Service Task", then choose "Next": "Permissions".
        4. In the "Attach permissions policies" section, search for ```AmazonECSTaskExecutionRolePolicy, SecretsManagerReadWrite, ECR_FullAccess, AmazonECS_FullAccess, ElastioBackupAdmin``` select "Policies", then choose "Next": "Tags".
        5. For Add tags (optional), specify custom tags to associate with the policy and then choose "Next": "Review".
        6. For Role name, type `ecs_task_execution_role` and choose "Create role".

3. Build and push a docker image:
    > You can find the latest version by following this link. https://gallery.ecr.aws/elastio-dev/elastio-cli
    1. Edit file contrib/elastio-ec2-backup-ecs-stopped-task/failed_ecs_handler_config.py and put data about topic, brokers, vault.
    2. Create ECR repository.
    3. Register your docker cli by getting the ecr public image with the command:
        ```aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws```
    4. Open the ECR repository you have created earlier and press the button "View push commands". The screen will list four commands. Run them in your terminal to build the docker image.
4. Create a Fargate Cluster.
    1. From the AWS console, select `Elastic Container Service`=>`Create Cluster`.
    2. Under "Select" cluster template, select "networking only".
    3. Enter your cluster name and press `Create`.
5. Create an ECS Task.
    1. Select `Task Definitions` from the left-side menu. Then choose `Create new task definition`.
    2. Select Fargate => "Next Step".
    3. Enter `Task definition name`.
    4. In the `Task role` field choose `ecs_task_execution_role`.
    5. Choose `Linux` as an operating system family.
    6. Task execution role.
    7. Task memory (GB): 4GB
    8. Task CPU (vCPU): 1vCPU
    9. Select `Add container`.
    10. Enter a container name.
    11. In the image field put URL of your docker image from ECR repository. Copy the arn from the ECS tab.
    12. Set `Private repository authentication` to true
    13. Memory Limits (MiB):
        1. Soft limit: `4096`
        2. Hard limit: `4096`
    14. Press `Add`.
    15. Lastly, press `Create` button.
6. Run the ECS schedule task.
    1. Select your cluster in ECS Clusters.
    2. In the navigation tab choose `Scheduled Tasks`.
    3. Press `Create` button.
    4. Enter `Schedule rule name`=>`Target id`.
    5. Launch type choose `Fargate`.
    6. Task Definition, choose your task definition.
    7. Select a VPC from the list in the Cluster VPC field.
    8. Add at least one subnet.
    9. Enable Auto-assign public IP.
    10. Press `Create` button. This will run the task according to the selected schedule.
7. Get logs.
    1. Open AWS Cloud Watch Service
    2. In the left side menu, choose `Logs`=>`Log group`.
    3. In the search field, enter your schedule task definition name.
    4. Choose in result your task definition with logs.