## Deploy Infrastructure with Ansible and Elastio

---
### Author: Robert Saylor
AWS Certified Cloud Practitioner

Email: customphpdesign@gmail.com


### Requirements
- Ansible
- boto2
- python3

### Pem Key
Copy your PEM key to the pem directory and set the proper permission. The filename must match the key name in AWS.

If your key name in AWS is my-ssh-key then the PEM filename would be my-ssh-key.pem

### Operating Systems

In this example we will cover Ubuntu 20.04 and AWS Linux 2.

- Ubuntu 20.04 marketplace AMI "[ami-08d4ac5b634553e16](https://aws.amazon.com/marketplace/pp/prodview-iftkyuwv2sjxi)"
- AWS Linux 2 marketplace AMI "[ami-0cff7528ff583bf9a](https://aws.amazon.com/marketplace/pp/prodview-wbr4b4xclx32c)"

>> Before using any AMI documented it is best to go to AWS > Click on Launch EC2 > and search for the AMI there.

### Playbook Parameters

- `ami` : This should be a valid AMI on the AWS Marketplace
- `ssh_key`: This is the name of your SSH key located on your AWS account
- `instance_type`: Example: t3.medium
- `os_type`: ubuntu | aws_linux (pass only one value)
- `security_group`: The security group ID
- `vpc_subnet_id`: The VPC subnet ID
- `region`: The region to deploy the new EC2. Example: [us-east-1](https://docs.aws.amazon.com/general/latest/gr/rande.html)
- `profile`: The IAM Profile with the permissions assigned

### IAM Role

From IAM click on Roles.

Click on Create role

Select AWS Service and select EC2 from the Common use cases.

Filter the policies you wish to assign to the role. Elastio comes with several pre-defined IAM policies, all starting with the prefix `Elastio`. Assign only the policies required to perform your operation to your role. See [Elastio Policies](https://docs.elastio.com/src/getting-started/elastio-policies.html) for more details.

Give the role a name and click create role.

>> Note: If you use other services such as S3, DynamoDB, etc you must also attach those permissions to your IAM role.

>> Note: The playbook assumes Ansible is being used with an IAM Role. If it is not you need to add the following to your ec2 section in the playbook:

```
aws_access_key: " pass in the AWS access key "
aws_secret_key: " pass in the AWS secret key "
```


### Example Playbook Commands

Ubuntu 20.04
```
ansible-playbook launch-new-ec2-with-elastio-playbook.yml --extra-vars "ami=ami-08d4ac5b634553e16 ssh_key=<<YOUR_SSH_KEY>> instance_type=t3.small os_type=ubuntu security_group=<<YOUR-SECURITY-GROUP-ID>> vpc_subnet_id=<<YOUR-SUBNET-ID>> region=us-east-1 profile=<<IAM_PROFILE_NAME>>"
```

AWS Linux 2
```
ansible-playbook launch-new-ec2-with-elastio-playbook.yml --extra-vars "ami=ami-0cff7528ff583bf9a ssh_key=<<YOUR_SSH_KEY>> instance_type=t3.small os_type=aws_linux security_group=<<YOUR-SECURITY-GROUP-ID>> vpc_subnet_id=<<YOUR-SUBNET-ID>> region=us-east-1 profile=<<IAM_PROFILE_NAME>>"
```
