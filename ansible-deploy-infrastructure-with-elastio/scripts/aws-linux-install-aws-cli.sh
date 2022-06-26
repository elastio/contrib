#!/bin/bash

PUBLIC_IP=$1
SSH_KEY=$2

ssh -i pem/${SSH_KEY}.pem ec2-user@${PUBLIC_IP} "curl \"https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip\" -o \"awscliv2.zip\""
ssh -i pem/${SSH_KEY}.pem ec2-user@${PUBLIC_IP} "unzip awscliv2.zip; sudo ./aws/install"
ssh -i pem/${SSH_KEY}.pem ec2-user@${PUBLIC_IP} "mkdir /home/ec2-user/.aws; echo \"[default]\" >> /home/ec2-user/.aws/config; echo \"region = us-east-1\" >> /home/ec2-user/.aws/config; echo \"output = json\" >> /home/ec2-user/.aws/config"
