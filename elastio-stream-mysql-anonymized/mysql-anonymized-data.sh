#!/bin/bash

DATABASE=$1
BACKUP_FILE=$2

mysqldump ${DATABASE} | /home/ubuntu/myanon/myanon-main/main/myanon -f /home/ubuntu/elastio_mysql/elastio.cnf | elastio stream backup --stream-name ${BACKUP_FILE}
