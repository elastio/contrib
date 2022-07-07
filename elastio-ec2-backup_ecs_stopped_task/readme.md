# Elastio EC2 backup ECS stopped task

## Step 1 - Create ECR polices

1. From AWS console, select "IAM service" => `Policies` => "Create Policy".
1. Under the **Service** tab select `Elastic Container Registry`.
1. Under the **Actions** tab select `All Elastic Container Registry actions (ecr:*)`.
1. Under the **Resources** tab select `specific` =>`Add ARN`.
    Then choose the region, leave your account number and
    select "Any" for the Repository name.
1. Enter 'ECR_FullAccess' as a policy name.

## Step 2 - Roles

1. From AWS console, select IAM service =>`Roles`.
1. If you already have a role for ECS tasks, add the following policies to the role:

    1. `AmazonECSTaskExecutionRolePolicy`
    1. `SecretsManagerReadWrite`
    1. `AmazonECS_FullAccess`
    1. `ECR_FullAccess`
    1. `ElastioBackupAdmin`

    or create a new role with these permissions.
Creating a new role follow these steps:

1. In the navigation pane, choose "Roles" =>"Create role".
1. In the "Select type of trusted entity section",
    choose "AWS service" => "Elastic Container Service".
1. In "Select your use case", select the "Elastic Container Service Task",
    then choose "Next": "Permissions".
1. In the "Attach permissions policies" section, search for

    1. `AmazonECSTaskExecutionRolePolicy`
    1. `SecretsManagerReadWrite`
    1. `AmazonECS_FullAccess`
    1. `ECR_FullAccess`
    1. `ElastioBackupAdmin`

    select "Policies", then choose "Next": "Tags".
1. For Add tags (optional), specify custom tags to
    associate with the policy and then choose "Next": "Review".
1. For Role name, type `ecs_task_execution_role` and choose "Create role".

## Step 3 - Build and push a docker image

> You can find the latest version by following this link.
<https://gallery.ecr.aws/elastio-dev/elastio-cli>

1. Edit file contrib/elastio-ec2-backup-ecs-stopped-task/failed_ecs_handler_config.py
    and put data about topic, brokers, vault.
1. Create ECR repository.
1. Register your docker CLI by getting the ECR public image with the command:

    ```console
    aws ecr-public get-login-password --region us-east-1 | \
    docker login --username AWS --password-stdin public.ecr.aws
    ```

1. Open the ECR repository you have created earlier
    and press the button "View push commands".
    The screen will list four commands.
    Run them in your terminal to build the docker image.

## Step 4 - Create a Fargate Cluster

1. From the AWS console, select `Elastic Container Service`=>`Create Cluster`.
1. Under "Select" cluster template, select "networking only".
1. Enter your cluster name and press `Create`.

## Step 5 - Create an ECS Task

1. Select `Task Definitions` from the left-side menu. Then choose
    `Create new task definition`.
1. Select Fargate => "Next Step".
1. Enter `Task definition name`.
1. In the `Task role` field choose `ecs_task_execution_role`.
1. Choose `Linux` as an operating system family.
1. Task execution role.
1. Task memory (GB): 4GB
1. Task CPU (vCPU): 1vCPU
1. Select `Add container`.
1. Enter a container name.
1. In the image field put URL of your docker image from ECR repository.
    Copy the arn from the ECS tab.
1. Set `Private repository authentication` to true
1. Memory Limits (MiB):
    1. Soft limit: `4096`
    1. Hard limit: `4096`
1. Press `Add`.
1. Lastly, press `Create` button.

## Step 6 - Run the ECS schedule task

1. Select your cluster in ECS Clusters.
1. In the navigation tab choose `Scheduled Tasks`.
1. Press `Create` button.
1. Enter `Schedule rule name`=>`Target id`.
1. Launch type choose `Fargate`.
1. Task Definition, choose your task definition.
1. Select a VPC from the list in the Cluster VPC field.
1. Add at least one subnet.
1. Enable Auto-assign public IP.
1. Press `Create` button.
    This will run the task according to the selected schedule.

## Step 7 - Get logs

1. Open AWS Cloud Watch Service
1. In the left side menu, choose `Logs`=>`Log group`.
1. In the search field, enter your schedule task definition name.
1. Choose in result your task definition with logs.
