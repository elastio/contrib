# Amazon RDS SQL Server

---

### Useful articles:
 - [Support for native backup and restore in SQL Server](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Appendix.SQLServer.Options.BackupRestore.html)
 - [Importing and exporting SQL Server databases using native backup and restore](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/SQLServer.Procedural.Importing.html)

### Requirements
- [ssstar](https://github.com/elastio/ssstar)
- SSMS or sqlcmd
- AWS CLI
- Elastio CLI

### Backup procedure
1. Create native backup of SQL on S3:
	1.1. Add `SQLSERVER_BACKUP_RESTORE` to an option group on your DB instance
    See: [Support for native backup and restore in SQL Server](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Appendix.SQLServer.Options.BackupRestore.html)
	1.2. Using SSMS or sqlcmd run query to create a backup:
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
2. Backup file from S3 using `elastio` and `ssstar`:
    ```
    ssstar create s3://s3-Bucket-Name --stdout \
        | elastio stream backup --hostname-override SQL-DB-Hostname --stream-name SQL-Db-Name
    ```
    See: `ssstar` [README.md](https://github.com/elastio/ssstar) and `elastio stream backup --help` for details.

### Restore procedure
1. Restore backup from `elastio` vault to S3:
    ```
    elastio stream restore --rp RP-ID \
        | ssstar extract --stdin s3://s3-Bucket-Name
    ```
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
2. Run `elastio block restore --rp RP-ID <drive letter>
3. Start MS SQL Server service

#### To the new location:
2. Run `elastio block restore --rp RP-ID <original drive letter>;<new drive letter>`
3. Using SSMS or sqlcmd attach restored database from new location