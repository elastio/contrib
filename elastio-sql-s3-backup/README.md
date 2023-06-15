This article describes the procedure of backup and restore Microsoft SQL server database. If your database hosted in Amazon RDS see [Amazon RDS SQL Server](https://github.com/elastio/contrib/blob/master/elastio-sql-s3-backup/README.md#amazon-rds-sql-server), if you have self hosted database see [self hosted SQL Server](https://github.com/elastio/contrib/blob/master/elastio-sql-s3-backup/README.md#self-hosted-sql-server).


# Amazon RDS SQL Server

---

### Useful articles:
 - [Support for native backup and restore in SQL Server](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Appendix.SQLServer.Options.BackupRestore.html)
 - [Importing and exporting SQL Server databases using native backup and restore](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/SQLServer.Procedural.Importing.html)

### Requirements
- SSMS or sqlcmd
- AWS CLI
- Elastio CLI

### Backup procedure
1. Add `SQLSERVER_BACKUP_RESTORE` to an option group on your DB instance

	See: [Support for native backup and restore in SQL Server](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Appendix.SQLServer.Options.BackupRestore.html)
3. Using SSMS or sqlcmd run query to create a backup:
	```
	exec msdb.dbo.rds_backup_database
		@source_db_name='database_name',
		@s3_arn_to_backup_to='arn:aws:s3:::bucket_name/file_name.extension',
		[@kms_master_key_arn='arn:aws:kms:region:account-id:key/key-id'],	
		[@overwrite_s3_backup_file=0|1],
		[@type='DIFFERENTIAL|FULL'],
		[@number_of_files=n];
	```
	See: [Importing and exporting SQL Server databases using native backup and restore](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/SQLServer.Procedural.Importing.html#SQLServer.Procedural.Importing.Native.Using.Backup)
3. Backup file from S3 using `elastio`:
	```
	elastio s3 backup --bucket s3-Bucket-Name
	```

### Restore procedure
1. Restore backup from `elastio` vault to S3:
	```
	elastio s3 generate-restore-iam-policy --bucket s3-Bucket-Name --account-id AWS-Account-ID

    aws iam create-role --role-name restoreDataBucketRole --assume-role-policy-document file://trust-policy.json

    aws iam put-role-policy --role-name restoreDataBucketRole --policy-name allowWriteToDataBucket --policy-document file://inline-policy.json

    elastio s3 restore --rp rp-ID --role-arn arn:aws:iam::[AWS-Account-ID]:role/restoreDataBucketRole --target-bucket s3-Bucket-Name --bucket-region AWS-Region

	```
	For help run: `elastio s3 generate-restore-iam-policy --help`	
	
2. Using SSMS or sqlcmd run query to restore from S3 to the RDS:
	```
	exec msdb.dbo.rds_restore_database
		@restore_db_name='database_name',
		@s3_arn_to_restore_from='arn:aws:s3:::bucket_name/file_name.extension',
		@with_norecovery=0|1,
		[@kms_master_key_arn='arn:aws:kms:region:account-id:key/key-id'],
		[@type='DIFFERENTIAL|FULL'];
	```
	See: [Importing and exporting SQL Server databases using native backup and restore](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/SQLServer.Procedural.Importing.html#SQLServer.Procedural.Importing.Native.Using.Restore)

# Self hosted SQL Server

---
### Requirements
- AWS CLI
- Elastio CLI

### Backup procedure
Backup volume with Microsoft SQL Server database using `elastio block backup` command:
```
elastio block backup <drive letter> --hostname-override SQL-DB-Hostname
```

### Restore procedure
#### To the same location:
1. Go to services and stop MS SQL Server service
2. Run `elastio block restore --rp RP-ID <drive letter>`
3. Start MS SQL Server service

#### To the new location:
2. Run `elastio block restore --rp RP-ID <original drive letter>;<new drive letter>`
3. Using SSMS or sqlcmd attach restored database from new location
