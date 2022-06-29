#!/bin/bash

PUBLIC_IP=$1
SSH_KEY=$2

ssh -i pem/${SSH_KEY}.pem ec2-user@${PUBLIC_IP} "curl \"https://raw.githubusercontent.com/elastio/elastio-stack/master/scripts/install-elastio.sh\" -o \"install-elastio.sh\""
ssh -i pem/${SSH_KEY}.pem ec2-user@${PUBLIC_IP} "sudo bash install-elastio.sh"
