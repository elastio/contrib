# Install Elastio

This playbook will setup a new Ubuntu server with some default software.

- Setup a new server and make sure the Ansible server can SSH into that new server without using a password.
- Add the new server to your local hosts file.
- Add the new server to your Ansible hosts file.
- You can add additional variables to your hosts file as needed.

## Hosts Example

```
[new_installs]
ubuntu_20_04_1 ansible_python_interpreter=/usr/bin/python3 ansible_user=ubuntu instance=i-08566adca0ff637c5
ubuntu_20_04_2 ansible_python_interpreter=/usr/bin/python3 ansible_user=ubuntu instance=i-0b899ee321425f261
ubuntu_20_04_3 ansible_python_interpreter=/usr/bin/python3 ansible_user=ubuntu instance=i-09177a97d31d6ca6e
ubuntu_20_04_4 ansible_python_interpreter=/usr/bin/python3 ansible_user=ubuntu instance=i-008d4426d97f5cf7d
ubuntu_20_04_5 ansible_python_interpreter=/usr/bin/python3 ansible_user=ubuntu instance=i-01c0aff71e074c9bc

```

## Playbook Example

### install-elastio.md

```
---
- hosts: new_installs
  tasks:

    - name: "Installing Ubuntu required packages"
      become: yes
      apt:
        state: present
        pkg:
          - unzip
          - jq

    - name: Download AWS CLI
      command: >
        curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"

    - name: Unzip AWS CLI
      command: >
        unzip awscliv2.zip

    - name: Install AWS CLI
      command: >
        sudo ./aws/install
      ignore_errors: True

    - name: Copy AWS credentials (1 of 2)
      file:
        path: /home/ubuntu/.aws
        state: directory

    - name: Copy AWS credentials (2 of 2)
      copy:
        src: /home/ubuntu/.aws/credentials
        dest: /home/ubuntu/.aws/credentials
        owner: ubuntu
        group: ubuntu
        mode: '0600'

    - name: Download Elastio CLI
      command: >
        curl "https://raw.githubusercontent.com/elastio/elastio-stack/master/scripts/install-elastio.sh" -o "install-elastio.sh"

    - name: Install Elastio CLI
      command: >
        sudo bash ./install-elastio.sh

```

## Bash scripts local to Ansible and config files

### .aws/credentials

```
[default]
aws_access_key_id=YOUR_ACCESS_KEY
aws_secret_access_key=YOUR_SECRET_ACCESS_KEY
region=us-east-1
output=json
```
