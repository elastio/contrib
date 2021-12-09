# A Step-by_Step Guide to Scanning the Local Repo Inside your CI Using Elastio's Integrity Scan (iscan) Module

**Note:** We will use GitLab in this example, but feel free to use any software version control tool you want.

## 1. Set up your CI environment

The first step is to set up your CI (Continuous Integration) environment. 

**Note:** To run Elastio on any operating system (OS), you must provide the credentials of the AWS account holding our Elastio Stack. As a result, to secure your credentials, you must add the following key-value pairs as variables to your repo: aws_access_key_id, aws_secret_access_key, and region.

## 2. Deploy Elastio inside your CI 

Here is a step-by-step guide to deploying Elastio inside your CI pipeline: 

### Step 1

To deploy Elastio inside your CI, you need to run the following command to creat the folder that AWS reads its credentials from: 

```
mkdir ~/.aws && touch ~/.aws/config ~/.aws/credentials 
```

### Step 2 

Once this command has successfully completed, the next step is to take the variables that you added to your repo and add them to the reated  `~/.aws/config ~/.aws/credentials` files as follows: 

``` 
    - |
      cat << END_TEXT > ~/.aws/config
        [default]
        region = $region
        output = text
      END_TEXT
    - |
      cat << END_TEXT > ~/.aws/credentials
        [default]
        aws_access_key_id = $aws_access_key_id
        aws_secret_access_key = $aws_secret_access_key
      END_TEXT
```
### Step 3

Run the following script in order to install the Elastio CLI and the Elastio Shell: 

```
- apt install unzip curl git wget -y
- /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com elastio/elastio-stack/ master/scripts/install-elastio.sh)"
- curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64 zip" -o "awscliv2.zip" && unzip awscliv2.zip && ./aws/install && apt install python3-pip -y
- pip3 install --extra-index-url=https://dl.cloudsmith.io public/elastio/public/python/simple/  elastio-shell
```

 ### Step 4

Run the follwown script to install the Integrity Scan (iscan) module: 

```
- curl --proto '=https' --tlsv1.2 -sSf https://raw.githubusercontent.com/elastio/elastio-stack/master/scripts/iscan > iscan
- chmod +x iscan
- mv iscan /usr/local/bin
 ```

### Step 5: 

Use iscan to scan the local repo for any malware before building the software application contained within the repo to ensure that your software is secure. 

**Note:** For this guide, we used the Elastio File Backup function to backup the following script called `malware.py`.

```python

import json
import subprocess
import os
variable = subprocess.Popen("cat iscan_malware.json",stdout=subprocess.PIPE,shell=True)
s = variable.stdout.read()
o = json.loads(s)
if o['infected'] == 0:
    print("No Threat Detected")
else:
    raise SystemExit('Warning Threat Detected ')     
          
```
This script examines the iscan results of your repo scan to ensure that the scan detected no malware before compiling and building the software application as a Docker image or performing any action on it. 

Once this script has been scanned, we will restore it and run it as part of our CI pipeline. 

```
- echo "n" | iscan -N "iscan"  --for malware ~/repo 
- tar -xf /tmp/iscan.tar.gz
- elastio file restore --rp r-dgm0tnd3ob3shl08fddrzj4w
- python3 malware.py
```

![set up project](https://i.ibb.co/Zdnxz6X/repo.png)

## 3. The final structure of the CI script that tests and builds the Docker image

Here is a copy of the Jenkins CI pipeline script that tests and builds the Docker image - using iscan to scan for malware before building the image:

```
image:
  name: jenkins/jenkins:lts
stages:
  - test
  - build
before_script:
    - apt-get update && apt-get -y install apt-transport-https ca-certificates curl gnupg2 software-properties-common
    - export DEBIAN_FRONTEND=$noninteractive
    - mkdir ~/.aws && touch ~/.aws/config ~/.aws/credentials
    - curl -fsSL https://download.docker.com/linux/$(. /etc/os-release; echo "$ID")/gpg > /tmp/dkey; apt-key add /tmp/dkey
    - add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/$(. /etc/os-release; echo "$ID") $(lsb_release -cs) stable"
    - apt-get update && apt-get -y install docker-ce
    - pwd
    - |
      cat << END_TEXT > ~/.aws/config
        [default]
        region = $region
        output = text
      END_TEXT
    - |
      cat << END_TEXT > ~/.aws/credentials
        [default]
        aws_access_key_id = $aws_access_key_id
        aws_secret_access_key = $aws_secret_access_key
      END_TEXT
    - apt install unzip  wget apt-transport-https ca-certificates curl software-properties-common git tar   python3-pip  wget -y
    - /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/elastio/elastio-stack/master/scripts/install-elastio.sh)"
    - curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && unzip awscliv2.zip && ./aws/install && apt install python3-pip -y
    
scan_repo:
  stage: test
  script:
    - elastio rp list
    - apt install unzip  wget apt-transport-https ca-certificates curl software-properties-common git tar   python3-pip  wget -y
    - /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/elastio/elastio-stack/master/scripts/install-elastio.sh)"
    - curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && unzip awscliv2.zip && ./aws/install && apt install python3-pip -y
    - curl --proto '=https' --tlsv1.2 -sSf https://raw.githubusercontent.com/elastio/elastio-stack/master/scripts/iscan > iscan
    - chmod +x iscan
    - mv iscan /usr/local/bin
    - echo "n" | iscan -N "iscan"  --for malware /builds/omar123456789101112/omg  
    - tar -xf /tmp/iscan.tar.gz
    - ls -l
    - elastio file restore --rp r-dgm0tnd3ob3shl08fddrzj4w 
    - python3 malware.py
  image:
    name: ubuntu:20.04
  services:
   - name: docker:19.03.13-dind
     alias: docker
  variables:
    DOCKER_HOST: tcp://docker:2375/
    # Use the overlayfs driver for improved performance:
    DOCKER_DRIVER: overlay2
    DOCKER_TLS_CERTDIR: ""
# this stage only run if test stage pased
docker-build:
  stage: build
  image:
    name: docker:19.03.13
  services:
   - name: docker:19.03.13-dind
     alias: docker
  variables:
    DOCKER_HOST: tcp://docker:2375/
    DOCKER_DRIVER: overlay2
    DOCKER_TLS_CERTDIR: ""
  before_script:
    - echo $CI_BUILD_TOKEN | docker login -u "$CI_REGISTRY_USER" --password-stdin $CI_REGISTRY
  script:
    - docker build --pull -t "$CI_REGISTRY_IMAGE:staging-$CI_COMMIT_REF_SLUG" .
    - docker push "$CI_REGISTRY_IMAGE:staging-$CI_COMMIT_REF_SLUG"
  only:
    - main
```


