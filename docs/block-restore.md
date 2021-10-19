# Block restore using 

You should have set up a 2nd volume and formatted as a partition to restore the backed up partition to the target partition.

You should have the following setup on your local Ansible server:

- Elastio
- JQ

## Installing JQ on Ubuntu 20.04 and 18.04

The playbook will install jq if you are using Ubuntu.

```
sudo apt-get update
sudo apt-get install jq
```

## Playbook Example

### host example

```
[new_ubuntu_hosts]
ubuntu_20_04_1 ansible_python_interpreter=/usr/bin/python3 ansible_user=ubuntu instance=i-08566adca0ff637c5 block1=nvme0n1p1 block2=nvme1n1p1
```

### playbook-ubuntu-block-restore.yml

```
---
- hosts: ubuntu_20_04_1

  tasks:

    # This is for Ubuntu. Update if rpm based.
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
        bash scripts/elastio_asset_get_recovery_point.sh {{ instance }} block
      register: recovery_point

    - name: Set default Elastio vault
      command: >
        elastio vault default default

    - name: "Restore block restore to /dev/{{ block2 }}"
      command: >
        sudo -E elastio block restore --rp {{ recovery_point.stdout }} /dev/{{ block1 }}:/dev/{{ block2 }}
      register: block_restore
      when: recovery_point.stdout != "error"
      failed_when: block_restore.rc != 0
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
