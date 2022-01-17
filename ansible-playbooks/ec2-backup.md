# EC2 backup using Elastio

You can back up an EC2 using elastio.

You should have the following setup on your target server:

- Elastio

## Playbook Example

### host example

```
[new_ubuntu_hosts]
ubuntu_20_04_1 ansible_python_interpreter=/usr/bin/python3 ansible_user=ubuntu instance=i-08566adca0ff637c5 block1=nvme0n1p1 block2=nvme1n1p1
```

### playbook-ubuntu-ec2-backup.yml

```
---
- hosts: new_ubuntu_hosts

  tasks:
    - name: Set default Elastio vault
      command: >
        elastio vault default default

    - name: EAP backup EC2
      command: >
        sudo -E elastio ec2 backup --instance-id {{ instance }}
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
