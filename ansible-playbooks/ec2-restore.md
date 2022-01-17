# EC2 restore using Elastio

  You can restore an EC2 using elastio.

You should have the following setup on target server:

  - Elastio
  - JQ
    
## Playbook Example

### host example

```
[new_ubuntu_hosts]
ubuntu_20_04_1 ansible_python_interpreter=/usr/bin/python3 ansible_user=ubuntu instance=i-08566adca0ff637c5 block1=nvme0n1p1 block2=nvme1n1p1
```

### playbook-ubuntu-ec2-restore.yml

```
---
- hosts: new_ubuntu_hosts

  tasks:
    - name: Set default Elastio vault
      command: >
        elastio vault default default

    # Update if using rpm based linux
    - name: "Installing Ubuntu required packages"
      become: yes
      apt:
        state: present
        pkg:
          - jq

    - name: Create scripts directory
      file:
        path: /home/ubuntu/scripts
        state: directory

    - name: Copy scripts
      copy:
        src: /home/ubuntu/ansible/scripts/elastio_asset_get_recovery_point.sh
        dest: /home/ubuntu/scripts/elastio_asset_get_recovery_point.sh
        owner: ubuntu
        group: ubuntu
      ignore_errors: True

    - name: Create output directory
      file:
        path: /home/ubuntu/output
        state: directory

    - name: "Get Last Recovery Point"
      command: >
        bash scripts/elastio_asset_get_recovery_point.sh {{ instance }} ec2
      register: recovery_point

    - name: "Elastio restore EC2"
      command: >
        sudo -E elastio ec2 restore --rp {{ recovery_point.stdout }}

```

## Bash Scripts : Store on the Ansible Server

### scripts/elastio_asset_get_recovery_point.sh

```
#!/bin/bash

SEARCH=$1
TYPE=$2

echo "$(elastio --output-format json rp list --type ${TYPE} | grep \"${SEARCH}\")" > output/asset_test.json
echo "$(cat output/asset_test.json | jq '.id')" > output/asset_test.txt
rpId=$(echo $(head -n 1 output/asset_test.txt) | sed 's/"//g')

if [[ $rpId =~ "r-" ]]; then
    echo "${rpId}"
  else
    echo "error"
fi
```
