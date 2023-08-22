# AWS RDS MySQL backup by Elastio and AWS Fargate

## Create AIM Role for Elastio Backup

1. Go to [AWS IAM Roles](https://console.aws.amazon.com/iamv2/home#/roles)
2. Press Create Role button
3. Select Elastic Container Service Task under Elastic Container Service for AWS service trusted entity and press Next
![image](https://github.com/elastio/contrib/assets/81738703/0a7050a0-895b-4227-a609-40bb9c6acb24)
4. Select `ElastioBackupAdmin` permission and press Next
5. Type `ElastioMySQLBackupRole` as a role name and press Create role
6. Open `ElastioMySQLBackupRole` and select Create inline policy under Add permissions
7. Select Secrets Manager and add `GetSecretValue` permission

## Create secret in AWS Secrets Manager
1. Go to [AWS Secrets Manager](https://console.aws.amazon.com/secretsmanager/listsecrets)
2. Press Store a new secrete button
3. Select `Credentials for Amazon RDS database` option
4. Specify the username and password for MySQL
5. Select the database from the list and press Next
![image](https://github.com/elastio/contrib/assets/81738703/5157852f-86c3-425e-bcc7-8a0a2a832a21)
6. Specify secret name, for example `MySQLBackupCreds` and press next
7. Review the secret and press Store

## Create ECS Task Definition

1. Go to [AWS Elastic Container Service Task definitions](https://console.aws.amazon.com/ecs/v2/task-definitions)
2. Press Create new task definition
3. Type `ElastioMySQLBackup` as a task definition family name
4. Select `ElastioMySQLBackupRole` as Task role
5. Type Elastio-CLI as container name
6. Paste `public.ecr.aws/elastio-dev/elastio-cli:latest` in container image URI
7. Expand Docker configuration and paste `sh,-c` in Entry point and following comman in Command:
```
apt-get install awscli jq default-mysql-client -y && creds=$(aws secretsmanager get-secret-value --secret-id MySQLBackupCreds | jq ".SecretString | fromjson") && mysqldump -h $(echo $creds | jq -r ".host") -u $(echo $creds | jq -r ".username") -P $(echo $creds | jq -r ".port") -p"$(echo $creds | jq -r '.password')" DATABASE | elastio stream backup --stream-name MySQL-Daily-backup --hostname-override MySQL-hostname
```
Where:
 - MySQLBackupCreds - name of the secret which stores credentials for MySQL database
 - DATABASE - name of the database for backup
 - MySQL-Daily-backup and MySQL-hostname - stream and host names that will be displayed in the Eastio tenant

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
