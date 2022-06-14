# Quick start

## Create an instance:
1. Create an EC2 instance (Amazon Linux 2 AMI (HVM) - Kernel 5.10, SSD Volume Type, instance type: t2.xlagre) in the same VPC as your MSK cluster.
2. Copy the name of the "Security Group" and save it for later. 
3. Open the Amazon VPC console at https://console.aws.amazon.com/vpc/.
4. In the navigation panel, select "Security Groups"'.
5. Find the "Security Group" that your MSK cluster uses.
6. Choose the correct row by checking the check box in the first column.
7. In the **Inbound Rules** tab, choose **Edit inbound rules** button. Then press the **Add rule** button.
8. In the New Rule field select **All traffic** in the **Type** column. In the second field of the **Source** column, select the "Security Group" of the client machine. Use the name you created on step 2.
9. Press the **Save rules** button. Now the cluster's Security Group can accept traffic that comes from the client machine's Security Group.

## Install requirements:
1. Clone the repository or download .zip file with the repository.
2. Before installing update your `pip`, copy and run the following command:
   
    ```
    python3 -m pip install --upgrade pip
   
    ```
3. Open **elastio-stream-kafka** directory in your terminal. <!--Discuss another naming-->
4. Install dependencies with the following command:
   
    ```
    python3 -m pip install -r requirements.txt
    ```

## Backup:
1. Open **elastio-stream-kafka** directory in your terminal. <!--Discuss another naming-->
2. To backup Kafka message, run `elastio_stream_kafka.py` script with the following arguments: **topic_name**, **brokers**, **vault**.<br/>
    
    Schema of arguments:
    
    ```
    python3 elastio_stream_kafka.py backup --topic_name <Name-of-your-topic> --vault <Name-of-your-vault> --brokers <broker1> <broker2> <broker3>
    ```
    
    Example:
    
    ```
    python3 elastio_stream_kafka.py backup --topic_name MSKTEST3 --vault defl --brokers b-2.elastio-stream-backup.3udh1w.c6.kafka.us-east-2.amazonaws.com:9092 b-3.elastio-stream-backup.3udh1w.c6.kafka.us-east-2.amazonaws.com:9092 b-1.elastio-stream-backup.3udh1w.c6.kafka.us-east-2.amazonaws.com:9092
    ```

## Restore:
1. Open **elastio-msk-kafka-stream** directory in your terminal. <!--Discuss another naming-->
2. Make sure that you have already created a topic for data recovery. The topic is not created automatically upon restore.
3. To restore Kafka message, run `elastio_stream_kafka.py` script with the following arguments: **topic_name**, **brokers**, **rp_id**.<br/>
    
    Schema of arguments:

    ```
    python3 elastio_stream_kafka.py restore --topic_name <Name-of-your-topic> --rp_id <Id-of-your-recovery-point> --brokers <broker1> <broker2> <broker3>
    ```
   
    Example:

    ```
    python3 elastio_stream_kafka.py restore --topic_name MSKTutorialTopic --rp_id rp-01g3c0cfm6mnejk5pmq4zheham --brokers b-2.elastio-stream-backup.3udh1w.c6.kafka.us-east-2.amazonaws.com:9092 b-3.elastio-stream-backup.3udh1w.c6.kafka.us-east-2.amazonaws.com:9092 b-1.elastio-stream-backup.3udh1w.c6.kafka.us-east-2.amazonaws.com:9092
    ```

## Scheduled backup with AWS ECS:
1. Create ECR polices:
    1. From AWS console, select "IAM service" =>`Policies` =>'Create Policy'.
    2. Under the **Service** tab select `Elastic Container Registry`.
    3. Under the **Actions** tab select `All Elastic Container Registry actions (ecr:*)`.
    4. Under the **Resources** tab select `specific` =>`Add ARN`. Then choose the region, leave your account number and select "Any" for the Repository name.
    5. Enter 'ECR_FullAccess' as a policy name.

2. Roles
    1. From AWS console, select IAM service =>`Roles`.
    2. If you already have a role for ECS tasks, add the following permissions: 
    ```AmazonECSTaskExecutionRolePolicy, SecretsManagerReadWrite, AmazonMSKFullAccess, ECR_FullAccess, ElastioFullAdmin``` or create a new role with these permissions.
        
        Creating a new role follow these steps:
        1. In the navigation pane, choose "Roles" =>"Create role".
        2. In the "Select type of trusted entity section", choose "AWS service" => "Elastic Container Service".
        3. In "Select your use case", select the "Elastic Container Service Task", then choose "Next": "Permissions".
        4. In the "Attach permissions policies" section, search for ```AmazonECSTaskExecutionRolePolicy, SecretsManagerReadWrite, AmazonS3FullAccess, ECR_FullAccess, ElastioFullAdmin``` select "Policies", then choose "Next": "Tags".
        5. For Add tags (optional), specify custom tags to associate with the policy and then choose "Next": "Review".
        6. For Role name, type `ecs_task_execution_role` and choose "Create role".

3. Build and push a docker image:
    > Before you start this section, review the dockerfile and read its comments.
    > You can find the latest version by following this link. https://gallery.ecr.aws/elastio-dev/elastio-cli
    1. Edit file contrib/elastio-stream-kafka/docker_backup_config.py and put data about topic, brokers, vault.
    2. Create ECR respository.
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
    > If you want to backup a topic from the AWS MSK, select the same VPC as you selected for MSK. Task Security Group has to accept Kafka traffic.
    7. Select a VPC from the list in the Cluster VPC field.
    8. Add at least one subnet.
    9. Enable Auto-assign public IP.
    10. Press `Create` button. This will run the task according to the selected schedule.
7. Get logs.
    1. Open AWS Cloud Watch Service
    2. In the left side menu, choose `Logs`=>`Log group`.
    3. In the search field, enter your schedule task definition name.
    4. Choose in result your task definition with logs.
