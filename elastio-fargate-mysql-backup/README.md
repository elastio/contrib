# AWS RDS MySQL backup by Elastio and AWS Fargate

## Create AIM Role for Elastio Backup

1. Go to [AWS IAM Roles](https://console.aws.amazon.com/iamv2/home#/roles)
2. Press Create Role button
3. Select Elastic Container Service Task under Elastic Container Service for AWS service trusted entity and press Next
![image](https://github.com/elastio/contrib/assets/81738703/0a7050a0-895b-4227-a609-40bb9c6acb24)
4. Select `ElastioBackupAdmin` permission and press Next
5. Type `ElastioMySQLBackupRole` as a role name and press Create role

## Create ECS Task Definition

1. Go to [AWS Elastic Container Service Task definitions](https://console.aws.amazon.com/ecs/v2/task-definitions)
2. Press Create new task definition
3. Type `ElastioMySQLBackup` as a task definition family name
4. Select `ElastioMySQLBackupRole` as Task role
5. Type Elastio-CLI as container name
6. Paste `public.ecr.aws/elastio-dev/elastio-cli:latest` in container image URI
7. Expand Docker configuration and paste `sh,-c` in Entry point and following comman in Command:
```
apt-get install default-mysql-client -y && mysqldump -h HOST -u USER -P PORT -p'PASSWORD' DATABASE | elastio stream backup --stream-name MySQL-Daily-backup --hostname-override MySQL-hostname
```
For example:
```
apt-get install default-mysql-client -y && \
  mysqldump -h database-1.cobsthon7f1g.us-east-1.rds.amazonaws.com -u admin -P 3306 -p'MySQLPassword' DemoDB | \
  elastio stream backup --stream-name MySQL-Daily-Backup --hostname-override database-1.cobsthon7f1g.us-east-1.rds.amazonaws.com
```
![image](https://github.com/elastio/contrib/assets/81738703/2ee7ebd2-b060-448e-a53d-f0082d5929ae)

8. Press Create

## Run on-demand MySQL backup with Elastio and AWS Fargate

1. Go to [AWS Elastic Container Service](https://console.aws.amazon.com/ecs/v2/)
2. Select an existing cluster or create new one
3. Go to cluster tasks and press Run new task
4. Select Launch type and select `ElastioMySQLBackup` for Task definition Family
5. Press Create

## Schedule automatic MySQL backup with Elastio and AWS Fargate

1. Go to [AWS Elastic Container Service](https://console.aws.amazon.com/ecs/v2/)
2. Select an existing cluster or create new one
3. Go to Scheduled tasks and press Create
4. Specify Schedule rule name, Schedule, Target id
5. Select FARGATE Launch type, `ElastioMySQLBackup` as Task Definition, VPC and Subnets
6. Press Create
