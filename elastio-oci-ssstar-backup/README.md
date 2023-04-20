# Oracle Autonomous Databases Backup by Elastio and ssstar

---

ssstar is a command-line tool to create and extract tar-compatible archives containing objects stored in S3 or S3-compatible storage. The resulting tar archive can be written to stdout and piped to `elastio` CLI for stream backup.

The following assumes you already have a database backup that is stored in Oracle Cloud Object Storage. To create a backup of Oracle database please refer to one of the following articles:
 - [Back Up a Database to Object Storage Using RMAN](https://docs.oracle.com/en-us/iaas/dbcs/doc/back-database-object-storage-using-rman.html)
 - [Use Data Pump to Create a Dump File Set on Autonomous Database](https://docs.oracle.com/en/cloud/paas/autonomous-database/adbsa/export-data-create-dump-file.html)

## Requirements
 - [ssstar](https://github.com/elastio/ssstar)
 - AWS CLI
 - Elastio CLI

## Backup

Amazon S3 Compatibility API is used to backup data from Oracle Object Storage to `elastio` vault. To access Amazon S3 Compatibility API use an existing or create a new Customer Secret Key. To create a Customer Secret Key, see [Create a Customer Secret key](https://docs.oracle.com/en-us/iaas/Content/Identity/Tasks/managingcredentials.htm#create-secret-key).

To do a onetime backup you need a Linux box with `ssstar`, AWS and `elastio` CLI installed. AWS CLI must be configured to access AWS account with `elastio` vault.

Run the following command to backup Oracle Object Storage to `elastio` vault:

```
ssstar create s3://{bucketname}/ --stdout \ 
  --s3-endpoint https://{bucketnamespace}.compat.objectstorage.{OCI-region}.oraclecloud.com \ 
  --aws-access-key-id {OCI-access-key} --aws-secret-access-key {OCI-secret-key} \ 
  --aws-region {OCI-region} | elastio stream backup --hostname-override oracle-cloud --stream-name oracle-database-backup
```
Where:
 - bucketname - Oracle Object Storage bucket name
 - bucketnamespace - top-level container for all buckets and objects, see [Understanding Object Storage Namespaces](https://docs.oracle.com/en-us/iaas/Content/Object/Tasks/understandingnamespaces.htm#Understanding_Object_Storage_Namespaces)
 - OCI-region - region where the Object Storage is located
 - OCI-access-key and OCI-secret-key - Customer Secret Key for Amazon S3 Compatibility API access
 
As a result of the backup a new recovery point will be created under Other Assets area in your `elastio` tenant. `--hostname-override oracle-cloud` value will be used as asset name. 

## Restore to Oracle Cloud

Run following command to restore Oracle database backup to Oracle Object Storage from `elastio` vault:
```
elastio stream restore --rp {RP-ID} | ssstar extract --stdin s3://{bucketname}/ \ 
  --s3-endpoint https://{bucketnamespace}.compat.objectstorage.{OCI-region}.oraclecloud.com \ 
  --aws-access-key-id {OCI-access-key} --aws-secret-access-key {OCI-secret-key} \ 
  --aws-region {OCI-region}
```
Where:
 - RP-ID - `elastio` recovery point ID with Oracle database backup
 - bucketname - Oracle Object Storage bucket name
 - bucketnamespace - top-level container for all buckets and objects, see [Understanding Object Storage Namespaces](https://docs.oracle.com/en-us/iaas/Content/Object/Tasks/understandingnamespaces.htm#Understanding_Object_Storage_Namespaces)
 - OCI-region - region where the Object Storage is located
 - OCI-access-key and OCI-secret-key - Customer Secret Key for Amazon S3 Compatibility API access
 
To restore Oracle database from Oracle Object Storage see, [Recover a Database from Object Storage](https://docs.oracle.com/en-us/iaas/dbcs/doc/recover-database-object-storage.html).

## Restore to AWS

Run following command to restore Oracle database backup to AWS S3 from `elastio` vault:
```
elastio stream restore --rp {RP-ID} | ssstar extract --stdin s3://{bucketname}
```
Where:
 - RP-ID - `elastio` recovery point ID with Oracle database backup
 - bucketname - AWS S3 bucket name
 
To restore Oracle database from AWS S3 see, [Amazon S3 integration](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/oracle-s3-integration.html).

## Automation

To run Oracle Object Storage backup by schedule please follow next steps:
1. Go to AWS ECS
2. Navigate to Task definitions menu item and press Create new task definition button
3. Set Task definition name to "oracle-object-storage-backup"
4. Under Container section fill in:
 - Name: elastio-cli
 - Image URI: public.ecr.aws/elastio-dev/elastio-cli:latest
5. Under Docker configuration section fill in:
 - Entry point: sh,-c
 - Command: 
```
ssstar create s3://{bucketname}/ --stdout \ 
  --s3-endpoint https://{bucketnamespace}.compat.objectstorage.{OCI-region}.oraclecloud.com \ 
  --aws-access-key-id {OCI-access-key} --aws-secret-access-key {OCI-secret-key} \ 
  --aws-region {OCI-region} | elastio stream backup --hostname-override oracle-cloud --stream-name oracle-database-backup
```
6. Under Environment section fill in:
 - CPU: 2
 - Memory: 8
 - Task role: ElastioLocalBackup
7. Leave everything else by default and press Create button
8. Go to Clusters menu item
9. Create new or use existent ECS cluster
10. Go to Scheduled tasks of the ECS cluster from step 9 and press Create button
11. Fill in "Schedule rule name", "Target id", setup "Schedule rule type", select:
 - Launch type: FARGATE
 - Task Definition: oracle-object-storage-backup
 - Cluster VPC, Subnets, Security groups
12. Leave everything else by default and press Create button.
