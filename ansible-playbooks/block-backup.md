# Block backup using Elastio

You can back up the block device using elastio.

You should have the following setup on your local Ansible server:

- Elastio

## Playbook Example

### host example

```
[new_ubuntu_hosts]
ubuntu_20_04_1 ansible_python_interpreter=/usr/bin/python3 ansible_user=ubuntu instance=i-08566adca0ff637c5 block1=nvme0n1p1 block2=nvme1n1p1
```

### playbook-ubuntu-block-backup.yml

```
---
- hosts: new_ubuntu_hosts

  tasks:

    - name: Create scripts directory
      file:
        path: /home/ubuntu/scripts
        state: directory

    - name: Copy scripts
      copy:
        src: /home/ubuntu/ansible/scripts/block_device.sh
        dest: /home/ubuntu/scripts/block_device.sh
        owner: ubuntu
        group: ubuntu
      ignore_errors: True

    - name: Set default Elastio vault
      command: >
        elastio vault default default

    # The following will return the block device
    - name: Get block device
      command: >
        bash scripts/block_device.sh
      register: block_device

    # The following will backup the block device
    - name: EAP backup block device
      command: >
        sudo -E elastio block backup /dev/{{ block_device.stdout }}
      register: elastio_cmd1
      ignore_errors: True

    - name: Update cache
      become: yes
      apt:
        update_cache: yes
      when: elastio_cmd1.rc == 0

    - name: Upgrade all packages on servers
      become: yes
      apt:
        name: "*"
        state: latest
      when: elastio_cmd1.rc == 0

```

## Bash Scripts : Store on the Ansible Server

### scripts/block_device.sh

```
#!/bin/bash
lsblk -l --output NAME,TYPE | grep part | cut -d ' ' -f1
```
