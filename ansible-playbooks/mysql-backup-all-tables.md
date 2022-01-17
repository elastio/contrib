# MySQL Backup using Elastio

The example playbook below will call a bash script to perform a MySQL backup on each table in your database.

You should have the following setup on your local Ansible server:

- .my.cnf file setup
- MySQL Client
- JQ (Used with restore)
- Elastio

## .my.cnf example

```
[client]
password="yourMySQLPassword"
user=yourmysqlusername
host=xxx-changeme-xxx.us-east-1.rds.amazonaws.com

[mysqldump]
password="yourMySQLPassword"
user=yourmysqlusername
host=xxx-changeme-xxx.us-east-1.rds.amazonaws.com
```

## Playbook Example

### playbook-rds-backup-individual-tables.yml

```
- name: "RDS Database"
  hosts: localhost
  connection: local
  tasks:

    - name: "Check if variable database has a value."
      fail: msg="The variable 'database' is not defined or empty. Please review usage."
      when: (database is not defined) or (database|length == 0)

    - name: "Backup each table."
      command: >
        bash scripts/mysql_backup_individual_tables.sh {{ database }}
      register: elastio_cmd1
      failed_when: elastio_cmd1.rc != 0
```
### scripts/mysql_backup_individual_tables.sh

```
#!/bin/bash

DATABASE=$1
TODAY=$(date +%F)

TABLES=$(mysql -e "SHOW TABLES;" ${DATABASE} | xargs)
for table in ${TABLES}; do
  mysqldump ${DATABASE} ${table} --set-gtid-purged=OFF | elastio stream backup ${DATABASE}-${table}-${TODAY}.sql --tag ${DATABASE}:${table}:${TODAY}
done
```

### Usage

```
ansible-playbook playbook-rds-backup-individual-tables.yml --extra-vars "database=databasename"
```
