# Oracle Backup via RMAN, ssstar and Elastio

---

Script uses `rdsadmin.rdsadmin_rman_util` and `rdsadmin.rdsadmin_s3_tasks.upload_to_s3` Amazon RDS procedures to backup Oracle DB instance and upload backed up files from your DB instance to an Amazon S3 bucket. Then streams the files to Elastio using `ssstar` utility.

**Useful articles:**
 - [Performing common RMAN tasks for Oracle DB instances](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Appendix.Oracle.CommonDBATasks.RMAN.html)
 - [Amazon S3 integration](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/oracle-s3-integration.html)

## Requirements
- [ssstar](https://github.com/elastio/ssstar)
- [Oracle Instant Client](https://www.oracle.com/database/technologies/instant-client/downloads.html)
- AWS CLI
- Elastio CLI

## Usage

Copy the script to instance with next software instelled:
- `ssstar`
- Oracle Instant Client including sqlplus
- AWS CLI
- `elastio` CLI

Test connection to the Oracle RDS instans:
```
sqlplus username/password@aws-rds-hostname:1521/SID
```
Make sure Elastio CLI is configured and has connection to the Elastio vault.

Change script variables (Oracle DB credentials, s3 bucket name) according to your environment configuration and run script:
```
oracleDbUser='admin'
oracleDbPassword='password'
oracleDbHostname='database1.cd4xq5de693v.us-east-2.rds.amazonaws.com'
oracleDbPort='1521'
oracleDbSID='ORCL'

s3BucketName='oracle2291'
oracleBackupDir='DATA_PUMP_DIR'
```

Script will create Oracle backup, upload backup to s3 bucket and stream files from s3 bucket to the elastio vault.