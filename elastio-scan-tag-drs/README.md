# Elastio DRS Source Server Tagging Script

This script allows you to manage the `elastio:action=scan` tag on AWS DRS (Elastic Disaster Recovery) source servers. 

---

## Features

- ✅ Add `elastio:action=scan` tag to **all** DRS source servers
- ✅ Add the tag to **specific** DRS source servers (by ID)
- ✅ Remove the tag from all servers

---

## Usage

### ✅ Run in AWS CloudShell

1. **Launch** [AWS CloudShell](https://console.aws.amazon.com/cloudshell/)
2. **Run the following command**:

```bash
wget -O elastio-tag-drs-source-server.sh https://github.com/elastio/contrib/raw/refs/heads/master/elastio-scan-tag-drs/elastio-tag-drs-source-server.sh && chmod +x elastio-tag-drs-source-server.sh && ./elastio-tag-drs-source-server.sh
