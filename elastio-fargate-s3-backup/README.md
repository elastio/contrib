# AWS S3 backup by Elastio and AWS Fargate

## Create AIM Role for Elastio Backup

1. Go to [AWS IAM Roles](https://console.aws.amazon.com/iamv2/home#/roles)
2. Press Create Role button
3. Select Elastic Container Service Task under Elastic Container Service for AWS service trusted entity and press Next
![image](https://github.com/elastio/contrib/assets/81738703/0a7050a0-895b-4227-a609-40bb9c6acb24)
4. Select ElastioBackupAdmin and AmazonS3ReadOnlyAccess permissions and press Next
5. Type ElastioS3Backup as a role name and press Create role

## Create ECS Task Definition

1. Go to [AWS Elastic Container Service Task definitions](https://console.aws.amazon.com/ecs/v2/task-definitions)
2. Press Create new task definition
3. Type ElastioS3Backup as a task definition family name
4. Type Elastio-CLI as container name
5. Paste `public.ecr.aws/elastio-dev/elastio-cli:latest` in container image URI
6. Expand Docker configuration and paste `sh,-c` in Entry point and `elastio s3 backup --bucket <S3 Bucket Name>` in Command. Where `<S3 Bucket Name>` is a name of your bucket for backup.
7. Press Next

8. Select ElastioS3Backup as Task role
9. Press Next and Create

## Run S3 backup by Elastio and AWS Fargate

1. Go to [AWS Elastic Container Service](https://console.aws.amazon.com/ecs/v2/)
2. Select an existing cluster or create new one
3. Go to cluster tasks and press Run new task
4. Select Launch type and select ElastioS3Backup for Task definition Family
5. Press Create

## Schedule S3 backup by Elastio and AWS Fargate

1. Go to [AWS Elastic Container Service](https://console.aws.amazon.com/ecs/v2/)
2. Select an existing cluster or create new one
3. Go to Scheduled tasks and press Create
4. Specify Schedule rule name, Schedule, Target id
5. Select FARGATE Launch type, ElastioS3Backup as Task Definition, VPC and Subnets
6. Press Create
