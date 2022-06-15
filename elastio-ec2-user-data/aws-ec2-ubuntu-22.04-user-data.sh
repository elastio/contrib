#!/bin/bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
apt install unzip
unzip awscliv2.zip
./aws/install
mkdir /home/ubuntu/.aws
echo "[default]" >> /home/ubuntu/.aws/config
echo "region = us-east-1" >> /home/ubuntu/.aws/config
echo "output = json" >> /home/ubuntu/.aws/config
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/elastio/elastio-stack/feat/5187-ubuntu2204/scripts/install-elastio.sh) $0" -- -b release-candidate
