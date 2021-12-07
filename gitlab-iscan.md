# Scan the local Repo inside your CI Using Elastio's iScan Feature  

#[Note in this example we are going to use gitlab but feel free to use any software version control tool you want]

## **1-Setup your CI environment**
### **(1) First to run elastio in any os you have to provide the credentials of the aws account holding our elastio stack so you will add the following as variables in your repo with thier values { aws_access_key_id , aws_secret_access_key,region } to secure your credintials** 
## **2-Deploy elastio inside your CI**
### **(1) In the CI we run the command { ``` mkdir ~/.aws && touch ~/.aws/config ~/.aws/credentials ``` } to create the folder that AWS reads its credentials from
### **(2) then we run the second command which take the variables that we added to the repo and adds them to the created  ~/.aws/config ~/.aws/credentials files
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

### **(3) we follow the Elastio docs to install `elastio` so we run the following commands**
```
- apt install unzip curl git wget -y
- /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com elastio/elastio-stack/ master/scripts/install-elastio.sh)"
- curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64 zip" -o "awscliv2.zip" && unzip awscliv2.zip && ./aws/install && apt install python3-pip -y
- pip3 install --extra-index-url=https://dl.cloudsmith.io public/elastio/public/python/simple/  elastio-shell
```
### **(4) we follow the Elastio docs to install `iscan`**
```
- curl --proto '=https' --tlsv1.2 -sSf https://raw.githubusercontent.com/elastio/elastio-stack/master/scripts/iscan > iscan
- chmod +x iscan
- mv iscan /usr/local/bin
 ```

### **(5) we use iscan to scan the repo for any malware before building the project in the repo to make sure that our application is secure **
#### - we have used `elastio file backup` function before  to backup a script named `malware.py`
```

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
and we will restore it and run it in the pipeline and this script exams the iscan results of our repo to assure that no malware was detected before building the project to docker image  or performing any action on it

```
- echo "n" | iscan -N "iscan"  --for malware ~/repo 
- tar -xf /tmp/iscan.tar.gz
- elastio file restore --rp r-dgm0tnd3ob3shl08fddrzj4w
- python3 malware.py
```
![set up project](https://i.ibb.co/Zdnxz6X/repo.png)

## Finally the CI file should look like this

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


