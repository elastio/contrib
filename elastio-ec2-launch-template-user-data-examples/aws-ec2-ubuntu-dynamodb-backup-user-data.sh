#!/bin/bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
apt-get update
apt install unzip -y
apt install python3-boto3 -y
unzip awscliv2.zip
./aws/install
mkdir /home/ubuntu/.aws
echo "[default]" >> /home/ubuntu/.aws/config
echo "region = us-east-1" >> /home/ubuntu/.aws/config
echo "output = json" >> /home/ubuntu/.aws/config
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/elastio/elastio-stack/master/scripts/install-elastio.sh)"
cd /home/ubuntu
aws s3 cp s3://eap-dynamo-backup/DynamoElastio.py /home/ubuntu
python3 DynamoElastio.py -m backup -s ProductCatalog && elastio stream backup --stream-name ProductCatalog.json --from-file schema.json
EC2_INSTANCE_ID="`wget -q -O - http://169.254.169.254/latest/meta-data/instance-id || die \"wget instance-id has failed: $?\"`"
sleep 30
aws ec2 terminate-instances --instance-ids ${EC2_INSTANCE_ID}
