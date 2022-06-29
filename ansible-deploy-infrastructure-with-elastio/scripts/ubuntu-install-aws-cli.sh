#!/bin/bash

PUBLIC_IP=$1
SSH_KEY=$2

ssh -i pem/${SSH_KEY}.pem ubuntu@${PUBLIC_IP} "curl \"https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip\" -o \"awscliv2.zip\""
ssh -i pem/${SSH_KEY}.pem ubuntu@${PUBLIC_IP} "sudo apt install unzip -y; unzip awscliv2.zip; sudo ./aws/install"
ssh -i pem/${SSH_KEY}.pem ubuntu@${PUBLIC_IP} "mkdir /home/ubuntu/.aws; echo \"[default]\" >> /home/ubuntu/.aws/config; echo \"region = us-east-1\" >> /home/ubuntu/.aws/config; echo \"output = json\" >> /home/ubuntu/.aws/config"
