#!/bin/sh

oracleDbUser='admin'
oracleDbPassword='password'
oracleDbHostname='database1.cd4xq5de693v.us-east-2.rds.amazonaws.com'
oracleDbPort='1521'
oracleDbSID='ORCL'

s3BucketName='oraclebackup2291'
oracleBackupDir='DATA_PUMP_DIR'

#Execute Oracle backup and s3 upload script via sqlplus
sqlplus $oracleDbUser/$oracleDbPassword@$oracleDbHostname:$oracleDbPort/$oracleDbSID <<EOF
DECLARE 
V_TASKID VARCHAR2(100);
V_COUNT integer := 0;
V_LOG integer := 0;

BEGIN
/*Run full database backup*/
rdsadmin.rdsadmin_rman_util.backup_database_full(
        p_owner               => 'SYS', 
        p_directory_name      => '$oracleBackupDir',
        p_section_size_mb     => 2000);

/*Upload backup to s3 bucket*/
SELECT rdsadmin.rdsadmin_s3_tasks.upload_to_s3(
		p_bucket_name => '$s3BucketName',  
		p_directory_name => '$oracleBackupDir') 
INTO V_TASKID FROM DUAL;

/*Wait till log file with upload progress is created*/
WHILE V_LOG = 0 LOOP 
SELECT COUNT(1) INTO V_LOG FROM TABLE(rdsadmin.rds_file_util.listdir(p_directory=>'BDUMP')) 
WHERE filename='dbtask-'|| V_TASKID ||'.log';
END LOOP;

/*Wait till upload is completed*/
WHILE V_COUNT = 0 LOOP
SELECT count(*) INTO V_COUNT FROM table(rdsadmin.rds_file_util.read_text_file('BDUMP', 'dbtask-'|| V_TASKID ||'.log')) 
WHERE text LIKE '%finished successfully%';
END LOOP;

END;
/
EOF

#Stream archive from s3 to elastio via ssstar
ssstar create s3://$s3BucketName --stdout \
  | elastio stream backup --hostname-override $oracleDbHostname --stream-name $oracleDbSID