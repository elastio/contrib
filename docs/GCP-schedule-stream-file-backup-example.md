# Elastio Scheduled Stream,File and Block Backup On GCP
## Compute instances:
### The approach is to use Google Instance scheduler to schedule an instance to start on an hourly basis.
```
```

## Requirements
### The minimum RAM required to run ```elastio stream backup``` and ```elastio block backup``` is 1GB or less so the recommended instance size is the F1 Micro with monthly cost around $7.11.  
``
``
### The minimum RAM required to run ```elastio file backup``` is 2GB so the recommended instance size is E2 Small with monthly cost around $13.23.  

``
``
### In all cases cases, the cost will reduce because the instance is only run to perform the backup then terminated.  
``
``
### We recommend using a mix of cron jobs and bash scripts to do basic recurring backups.  The recommended approach is to use cronjobs to launch the script upon startup like so:

```
@reboot /root/elastio.sh
```

### The above crontab entry will run the script when the instance starts, and then the Instance scheduler will stop the instance when the backup is complete.

```
```
## Shell Script elastio.sh

`#!/bin/bash
# Script to periodically run mysqldump & elastio backup

DB="world"
DIR="/backup/db"
d=$(date +%m-%d-%H)

# Taking mysqldump
mysqldump $DB | elastio stream backup --stream-name gcp-db-$d --tag app=db,date=$d

# Poweroff Instance
poweroff` 
