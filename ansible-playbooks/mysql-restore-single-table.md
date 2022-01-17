# MySQL Restore using Elastio

The example playbook below will call a bash script to perform a MySQL backup on each table in your database.

You should have the following setup on your local Ansible server:

- .my.cnf file setup
- MySQL Client
- JQ (Used with restore)
- Elastio
- Create the following directory: /home/ubuntu/output; /home/ubuntu/scripts

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

## Installing JQ on Ubuntu 20.04 and 18.04

```
sudo apt-get update
sudo apt-get install jq
```

## Playbook Example

### playbook-rds-restore-individual-table.yml

```
---
- name: "RDS Database"
  hosts: localhost
  connection: local
  tasks:

    - name: "Check if variable database has a value."
      fail: msg="The variable 'database' is not defined or empty. Please review usage."
      when: (database is not defined) or (database|length == 0)

    - name: "Check if variable table has a value."
      fail: msg="The variable 'table' is not defined or empty. Please review usage."
      when: (table is not defined) or (table|length == 0)

    - name: "Set default for date"
      set_fact: date="default"
      when: (date is not defined) or (date|length == 0)

    - name: "Get Last Recovery Point"
      command: >
        bash scripts/elastio_get_table_recovery_point.sh {{ database }} {{ table }} {{ date }}
      register: recovery_point
      failed_when: recovery_point.stdout == "error"

    - name: "Restore MySQL Table"
      command: >
        bash scripts/mysql_restore.sh {{ database }} {{ recovery_point.stdout }}
      register: elastio_cmd1
      when: recovery_point.stdout != "error"
      failed_when: elastio_cmd1.rc != 0
```

## Bash Scripts

### scripts/elastio_get_table_recovery_point.sh

```
#!/bin/bash

DATABASE=$1
TABLE=$2
DATE=$3

if [ "$DATE" == "default" ]; then
  DATE=$(date +%F)
fi

SEARCH="${DATABASE}-${TABLE}-${DATE}.sql"

echo "$(elastio --output-format json rp list | grep \"${SEARCH}\")" > output/rds_test.json
echo "$(cat output/rds_test.json | jq '.id')" > output/rds_test.txt
rpId=$(echo $(head -n 1 output/rds_test.txt) | sed 's/"//g')

if [[ $rpId =~ "r-" ]]; then
    echo "${rpId}"
  else
    echo "error"
fi
```

### scripts/mysql_restore.sh

```
#!/bin/bash

DATABASE=$1
RECOVERY_POINT=$2

elastio stream restore --to-stdout --rp ${RECOVERY_POINT} | mysql ${DATABASE}
```

### Usage

- The date field is optional. If not specified today's date will be used.

```
ansible-playbook {filename} --extra-vars "database=databasename table=tablename date=YYYY-MM-DD
```
