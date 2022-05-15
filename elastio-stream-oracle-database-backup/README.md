# Oracle Backup via AWS S3 and Elastio

---

The Oracle backup script allows you to easily back-up to a DUMP file to AWS S3. The backup script then streams the file to Elastio.

## Requirements
- AWS Oracle on RDS
- AWS S3 Integration
- EC2 client with Oracle Software
- AWS CLI
- Elastio CLI

## Assumptions

> This script assumes you have followed online tutorials to setup AWS S3 Integration with your Oracle RDS database.
> 
> Some useful tools:

[Oracle RDS S3 Integration](https://www.youtube.com/watch?v=XoN8gPbyjJ8&t)

[Importing using Oracle Data Pump - Amazon Relational Database Service](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Oracle.Procedural.Importing.DataPump.html#Oracle.Procedural.Importing.DataPumpS3.Step2)

## Installation

> Copy .env.sample to .env then add your database username, password and RDS host endpoint to the .env file

## EC2 Client

> Setup a Ubuntu 20.04 server and install AWS CLI and Elastio CLI. Then download and install the required Oracle software for the script to communicate to the Oracle database.

[Download the following from Oracle. Note: The versions may change depending on when you download them.](https://www.oracle.com/database/technologies/instant-client/linux-x86-64-downloads.html)

- oracle-instantclient-basic-21.6.0.0.0-1.el8.x86_64.rpm
- oracle-instantclient-devel-21.6.0.0.0-1.el8.x86_64.rpm
- oracle-instantclient-sqlplus-21.6.0.0.0-1.el8.x86_64.rpm
- oracle-instantclient-tools-21.6.0.0.0-1.el8.x86_64.rpm

[Install Alien](https://zoomadmin.com/HowToInstall/UbuntuPackage/alien)

> Install Oracle Software

```
sudo alien -i -c oracle-instantclient-basic-21.6.0.0.0-1.el8.x86_64.rpm
sudo alien -i -c oracle-instantclient-devel-21.6.0.0.0-1.el8.x86_64.rpm
sudo alien -i -c oracle-instantclient-sqlplus-21.6.0.0.0-1.el8.x86_64.rpm
sudo alien -i -c oracle-instantclient-tools-21.6.0.0.0-1.el8.x86_64.rpm
```

> Test your SQL connection

```
sqlplus username/password@aws-rds-hostname:1521/DATABASENAME
```

## Running the backup script

```
bash backup-oracle-table.sh database_name s3_bucket_name table_name
```

## Script in action

[Watch the script run in action](https://asciinema.org/connect/9903b254-91a1-4377-be15-376d199cbda4)
