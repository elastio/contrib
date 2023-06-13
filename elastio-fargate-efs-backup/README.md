# AWS EFS backup by Elastio and AWS Fargate

---

## Prerequisites
 - Elastio is installed and configured
 - EFS file system is available


## Create AIM Role for Elastio Backup

1. Go to [AWS IAM Roles](https://console.aws.amazon.com/iamv2/home#/roles)
2. Press Create Role button
3. Select Elastic Container Service Task under Elastic Container Service for AWS service trusted entity and press Next
4. Select ElastioBackupAdmin permission and press Next
5. Type ElastioEFSBackup as a role name and press Create role

## Create ECS Task Definition

1. Go to [AWS Elastic Container Service Task definitions](https://console.aws.amazon.com/ecs/v2/task-definitions)
2. Press Create new task definition
3. Type ElastioEFSBackup as a task definition family name
4. Type Elastio-CLI as container name
5. Paste `public.ecr.aws/elastio-dev/elastio-cli:latest` in container image URI
6. Expand Docker configuration and paste `sh,-c` in Entry point and `elastio file backup /mnt/efs --iscan --hostname-override Elastio-EFS-Backup` in Command
7. Press Next
8. Select 4 vCPU and 8 (or higher) GB of Memory
9. Select ElastioEFSBackup as Task role
10. Press Add volume in Storage section
11. Select EFS as Volume type, type ElastioEFSBackup in Volume name and select File system ID for backup
12. Press Add mount point, select Elastio-CLI as Container, ElastioEFSBackup as Source volume and `/mnt/efs` as Container path
13. Press Next and Create

## Run EFS backup by Elastio and AWS Fargate

1. Go to [AWS Elastic Container Service](https://console.aws.amazon.com/ecs/v2/)
2. Select an existing cluster or create new one
3. Go to cluster tasks and press Run new task
4. Select Launch type and select ElastioEFSBackup for Task definition Family
5. Press Create

## Schedule EFS backup by Elastio and AWS Fargate

1. Go to [AWS Elastic Container Service](https://console.aws.amazon.com/ecs/v2/)
2. Select an existing cluster or create new one
3. Go to Scheduled tasks and press Create
4. Specify Schedule rule name, Schedule, Target id
5. Select FARGATE Launch type, ElastioEFSBackup as Task Definition, VPC and Subnets
6. Press Create