# Oracle Autonomous Databases Backup by Elastio and ssstar

---

ssstar is a command-line tool to create and extract tar-compatible archives containing objects stored in S3 or S3-compatible storage. The resulting tar archive can be written to stdout and piped to `elastio` CLI for stream backup.

The following assumes you already have a database backup that is stored in Oracle cloud object storage. To create a backup of Oracle database please refer to one of the following articles:
 - [Back Up a Database to Object Storage Using RMAN](https://docs.oracle.com/en-us/iaas/dbcs/doc/back-database-object-storage-using-rman.html)
 - [Use Data Pump to Create a Dump File Set on Autonomous Database](https://docs.oracle.com/en/cloud/paas/autonomous-database/adbsa/export-data-create-dump-file.html)

## Requirements
 - [ssstar](https://github.com/elastio/ssstar)
 - AWS CLI
 - Elastio CLI

## Backup

Amazon S3 Compatibility API is used to backup data from Oracle Object Storage to `elastio` vault. To access Amazon S3 Compatibility API use an existing or create a new Customer Secret Key. To create a Customer Secret Key, see [Create a Customer Secret key](https://docs.oracle.com/en-us/iaas/Content/Identity/Tasks/managingcredentials.htm#create-secret-key).

To do a onetime backup you need a Linux box with configured AWS CLI, `ssstar` and `elastio` CLI installed. AWS CLI must be configured to access AWS account with `elastio` installed.

Run following command to backup Oracle Object Storage to `elastio` vault:

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
 
 To restore Oracle database from Oracle Object Storage see, [Recover a Database from Object Storage](https://docs.oracle.com/en-us/iaas/dbcs/doc/recover-database-object-storage.html)