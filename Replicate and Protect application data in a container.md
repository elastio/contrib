# Replicate and Protect application data and logs between deployments with one click using Elastio, Circleci and AWS/ECS.

![set up project](https://i.ibb.co/VwVyqKS/image.png,) 

## **Problem:-**
## Common problems that engineers usually face when deploying applications
### 1- When deploying a new application versions, features or instances, its easy to lose the original working directories and log files.  This is a repeated problem with each new deployment limiting the visibility into the development process and creating an recovery gab between each version.
### 2- When  developers want to test a new version of the app in a new environment quickly without affecting the running dev environment.  
## **Solution:-**
### Using elastio data protection as code approach you can guarantee the availability of the container persistent data and logs across each version without having to do any manual work. This approach automates the process and provides test/dev flexibility while save you a lot of time.  
 -------
## We will use a standard LAMP web application for this example
 ### Requirements 
* Create Circleci account  
* Create ECS cluster ,visit here  https://docs.aws.amazon.com/AmazonECS/latest/developerguide/create-ec2-cluster-console-v2.htmlto learn more
* 1 Database instance
* 1 kubernetes cluster

### Install
1. Download this project from this link https://www.dropbox.com/sh/zf7v5k4yx5c9270/AACycPFfLMsJOgDFSQzYsHkBa?dl=0 and add it to your circleci repo
3. install Mysql in the DB instances

# **Step 1: simple_lamp Mysql Database maintenance Steps:**

**[in the DB instance]**

After successfully installing Mysql, create the MySQL Database that the app will use and then create a MySQL user for our DB. Here we use “simple_lamp” as the database name, and “username” as the MySQL user. So we need to enter the following two commands:

```
   $ mysql -u root -p
   mysql> CREATE DATABASE simple_lamp;
   mysql> CREATE USER 'username'@'localhost' IDENTIFIED BY 'password';
   mysql> GRANT ALL PRIVILEGES ON simple_lamp.* TO 'username'@'localhost';
   mysql> quit

```
 #### \*keep in mind you must change ``localhost`` in the above commands to the ip of the instance holding the application

To make this tutorial simple we have a pre-populated demo data as example. We use the following command to import the demo data in simple_lamb.sql, see the project link above for a simple_lamp database:

``
$ mysql -u username -p simple_lamp < simple_lamp.sql
``
Edit the file config.php and change the Database connection parameters to the new parameters

After we finish modifying the app's files we use elastio to protect the app files in the folder lamp_project ``config.php``,``demo.js``,``index.php``,``uploads``,``uploads``  with the command:


``
  $ elastio file backup  lamp_project
``


# **Step 2: Using Elastio to backup the container local data and log files**:

**[in the kubernetes cluster]**

After we prepared the db instance we need to Dockerize our project before deploying it so we create a Dockerfile:

```
FROM ubuntu:latest
ENV DEBIAN_FRONTEND noninteractive
ARG AWS_DEFAULT_REGION
ENV AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION}
ARG AWS_ACCESS_KEY_ID
ENV AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
ARG AWS_SECRET_ACCESS_KEY
ENV AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
WORKDIR /app
COPY . /app
RUN apt-get update -y && \
 apt-get install -y apache2 php libapache2-mod-php  php-mysql php-curl php-xml php-memcached git curl unzip wget
RUN /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/elastio/elastio-stack/master/scripts/install-elastio.sh)" && \
        curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && unzip awscliv2.zip && ./aws/install
RUN service apache2 restart && mkdir  /var/www/html/simple-lamp && cp -r * /var/www/html/simple-lamp && chown -R www-data:www-data /var/www/html/simple-lamp/uploads
CMD ["apachectl", "-D", "FOREGROUND"]

```
Here we install elastio and awscli

``
RUN npm install && apt install curl unzip wget -y && /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/elastio/elastio-stack/master/scripts/install-elastio.sh)" && curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && unzip awscliv2.zip && ./aws/install ``

Here we install all the app dependencies

``
RUN apt-get update -y && \
	   apt-get install -y apache2 php libapache2-mod-php  php-mysql php-curl php-xml php-memcached git curl``


Before we can make it work, there are some minor modifications needed:

(1) we move the project to the path ``/var/www/html`` in the container.

(2) Use a text editor to open config.php, then change the username hostname and password for your MySQL installation.

(3) Change the ownership of folder “uploads” to “www-data” so that Apache can upload files to this folder.

``
 RUN service apache2 restart && mkdir  /var/www/html/simple-lamp && cp -r * /var/www/html/simple-lamp && chown -R www-data:www-data /var/www/html/simple-lamp/uploads
 ``

 (4) Then you need to restart  Apache on the web server container to make the new configuration effective and then start it.

``
 CMD ["apachectl", "-D", "FOREGROUND"]``

Finally, after the Dockerfile has been created and the project files are present we must enter the following commands to restore and build our lamp_project web-application:

``
  $ elastio file restore --rp
``

``
  $ cd lamp_project 
``


``
  $ docker build -t simple_lamp .
``

To run the application into our cluster we will use the following commands to create the deployment:

**1-Let’s define a PersistentVolume and the associated PersistentVolumeClaim in a single file:**
```
---
kind: PersistentVolume
apiVersion: v1
metadata:
  name: elastio-pv
  labels:
    type: local
spec:
  storageClassName: manual
  capacity:
    storage: 1Gi
  accessModes:
    - ReadWriteOnce
  hostPath:
    path: "/mnt/elastio-lamp"
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  labels:
    app: elastio
  name: elastio-pvc
spec:
  storageClassName: manual
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi

```
and in the path "/mnt/elastio-lamp" on the host we will place the images needed for the app to start with. These are present in the uploads folder. We define a PersistentVolume and the associated PersistentVolumeClaim in a single file:

**2-Having both the PersistentVolume and the PersistentVolumeClaim in place, the last step is to modify the Deployment manifest to obtain a volume via the PersistentVolumeClaim and mount it to the /var/www/html/simple-lamp/uploads directory.  This directory is used by our app to upload and store images:**
```
apiVersion: apps/v1
kind: Deployment
metadata:
  name: elastio-lamp
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: elastio
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 2
  template:
    metadata:
      labels:
        app: elastio
    spec:
      containers:
      - name: images
        image: 673281187890.dkr.ecr.us-east-1.amazonaws.com/images:3cb56914b0c6628f471ef2fab534e8f9ec266cbf
        ports:
        - name: lamp
          containerPort: 80
        volumeMounts:
        - mountPath: /var/www/html/simple-lamp/uploads
          name: config
      volumes:
        - name: config
          persistentVolumeClaim:
            claimName: elastio-pvc
      imagePullSecrets:
      - name: regcred
---
apiVersion: v1
kind: Service
metadata:
  name: elastio-lamp-svc
spec:
  ports:
  - port: 80
    nodePort: 31513
    targetPort: lamp
    protocol: TCP
  selector:
   app: elastio
  type: NodePort

```
Let’s now apply the new manifest, which will trigger a scheduling of  the deployment's pod and service:

-To verify if the applications works, let's go to the web-browser and enter the following URL-address and replace instance-ip with your ip :
                           { http://instance-ip:31513/simple-lamp}

![set up project](https://i.ibb.co/4mGk39t/done.png)



- So we assume that we transform our log files into a .zip file and to make its easily available we will use `elastio` in a cronjob to protect the .zip logs every hour using the following commands. 
- As we have seen, our docker persistent volume will hold the uploaded images in the folder ``uploads`` in the pod.  We will use `elastio` in a cronjob to protect this directory every day using the following commands 

--we create 2 cron jobs

``$ sudo crontab -e``

**1-**
that protect our logs every hour by running the following commands:

Add this line which will stream backup the zip file that contain the logs 

``0 * * * * wget https://filebin.net/archive/zory08bnkmhh3jki/zip && elastio file backup zip  --vault traum``

**2-**
that protect the directory, that holds the containers app files, every day at midnight. This will be added on the machine hosting the persistent volume

``0 0 * * * elastio file backup /var/www/html/simple-lamp/uploads --vault traum``
# **Step 3: Continuous deployment pipeline to deploy the simple lamp application from kubernetes to AWS ECS  using CircleCI**:

### Requirements

* CircleCI
* AWS ECS
* AWS ECR (to store the image in)
1. Create the CircleCI account

2. Create a GitHub repository

### Install

### 1. Download or clone this project

### 2. Push this project to your GitHub repository

### 3. In CircleCI setup the project add the config.yml and add the following to it

```
    ecr-build:
          docker:
            - image: 'cimg/python:3.9.1'
          steps:
             - checkout
             - setup_remote_docker:
                docker_layer_caching: false 
             - aws-cli/setup:
                  aws-access-key-id: AWS_ACCESS_KEY_ID 
                  aws-region: AWS_DEFAULT_REGION
                  aws-secret-access-key: AWS_SECRET_ACCESS_KEY
             - run: 
                 name: Install elastio and restore log file  
                 command: |
                        sudo apt install curl unzip -y
                        sudo /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/elastio/elastio-stack/master/scripts/install-elastio.sh)" 
                        elastio file restore --host  i-04c654191dd1da687 --rp @  --overwrite && sudo unzip zip
```
in this job we configure AWS credentials and install elastio ``sudo /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/elastio/elastio-stack/master/scripts/install-elastio.sh)"``  and restore the latest stream backup ``--rp @`` of the logs files in a specific host ``--host  elastio-lamp-5bc6c4479d-qx94s  `` 
```
 - run:
                 name: Build and push Docker image to ECR registry
                 command: |
                    pwd && ls -l
                    aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin 673281187890.dkr.ecr.us-east-1.amazonaws.com
                    docker build --build-arg AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} --build-arg AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} --build-arg AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION} -t ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_DEFAULT_REGION}.amazonaws.com/images:${CIRCLE_SHA1} . s
                    docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_DEFAULT_REGION}.amazonaws.com/images:${CIRCLE_SHA1}
``` 
then after we have restored the log files in the pipeline we build the image with the AWS env ``varriables AWS_ACCESS_KEY_ID`` ``AWS_SECRET_ACCESS_KEY`` , ``AWS_DEFAULT_REGION`` and push it to the ECR repo 

here is the whole config.yml file 


```
version: 2.1
orbs:
  aws-eks: circleci/aws-eks@1.1.0
  kubernetes: circleci/kubernetes@0.4.0
  aws-ecr: circleci/aws-ecr@0.0.2
  aws-ecs: circleci/aws-ecs@0.0.10
  aws-ecs1: circleci/aws-ecs@2.0
  aws-cli: circleci/aws-cli@1.3
  orb-tools: circleci/orb-tools@10.0
jobs:

    ecr-build:
          docker:
            - image: 'cimg/python:3.9.1'
          steps:
             - checkout
             - setup_remote_docker:
                docker_layer_caching: false 
             - aws-cli/setup:
                  aws-access-key-id: AWS_ACCESS_KEY_ID 
                  aws-region: AWS_DEFAULT_REGION
                  aws-secret-access-key: AWS_SECRET_ACCESS_KEY
             - run: 
                 name: Install elastio and restore log file  
                 command: |
                        sudo apt install curl unzip -y
                        sudo /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/elastio/elastio-stack/master/scripts/install-elastio.sh)" 
                        elastio file restore --host  i-04c654191dd1da687 --rp @  --overwrite && sudo unzip zip
             - run:
                 name: Build and push Docker image to ECR registry
                 command: |
                    pwd && ls -l
                    aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin 6789087890.dkr.ecr.us-east-1.amazonaws.com
                    docker build -t ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_DEFAULT_REGION}.amazonaws.com/images:${CIRCLE_SHA1} .
                    docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_DEFAULT_REGION}.amazonaws.com/images:${CIRCLE_SHA1}

workflows:
  version: 2
  build-and-deploy: 
    jobs:
      - ecr-build:
      - aws-ecs/deploy-service-update:
          requires:
            - ecr-build
          aws-region: ${AWS_DEFAULT_REGION}
          family: "lamp"
          service-name: "${AWS_RESOURCE_NAME_PREFIX}-service"
          cluster-name: "${AWS_RESOURCE_NAME_PREFIX}-cluster"
          container-image-name-updates: "container=${AWS_RESOURCE_NAME_PREFIX},image-and-tag=${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_DEFAULT_REGION}.amazonaws.com/${AWS_RESOURCE_NAME_PREFIX}:${CIRCLE_SHA1}"
          verify-revision-is-deployed: true

``` 

Once on the Project page, find the project you are using and click Set Up Project.

![set up project](https://github.com/andresaaap/cicd-only-deploying-circleci/blob/main/img/set-up-project.png?raw=true)

According to the AWS ECS orb’s repo it is very important to meet these requirements before running the pipeline:

Add the AWS credentials as environment variables. Configure `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` and `AWS_DEFAULT_REGION` as CircleCI project or context environment variables as shown in the links provided for [project](https://circleci.com/docs/2.0/env-vars/#setting-an-environment-variable-in-a-project) or [context](https://circleci.com/docs/2.0/env-vars/#setting-an-environment-variable-in-a-context).

![create environment variables](https://github.com/andresaaap/cicd-only-deploying-circleci/blob/main/img/create-env-variables.png?raw=true)


### 4. We go to the ECS cluster and add this task definition to it 

```

{
  "requiresCompatibilities": [
    "EC2"
  ],
  "containerDefinitions": [
    {
      "name": "images",
      "image": "$your-image"
      "cpu": 256,
      "essential": true,
      "entryPoint": [
                "sh",
                "-c"
            ],
            "command": [
                "/bin/sh -c \elastio file restore --host  i-04c65419ike1da687 --rp @  --overwrite && cp -r zip /var/log/lamp && apachectl -D FOREGROUND\""
            ],
      "portMappings": [
        {
          "containerPort": 80,
          "protocol": "tcp"
        }
      ],
      "logConfiguration": {
          "logDriver": "awslogs",
          "options": {
              "awslogs-group": "awslogs-elastio-lamp-ecs",
              "awslogs-region": "us-east-1",
              "awslogs-stream-prefix": "lamp"
          }
      }
    }
  ],
  "volumes": [],
  "networkMode": "bridge",
  "placementConstraints": [],
  "family": "lamp"
}

```
#### Notice in the task definition above, we restored the old container app data ``elastio file restore --host  i-04c65419ike1da687 --rp @`` and copied the logs file that we stream restored in circleci into its place ``cp -r zip /var/log/lamp`` and started the app  ``apachectl -D FOREGROUND`` all at launch time. Now when the developers need to test the functional running app in a new environment or launch a new version with the exact same app files and log files in place  they can do it with just one click.

# Step 4. Usage

- Run the Pipeline by pushing a new commit to the GitHub repository or manually in the project’s GUI in CircleCI.  This will activate the pipeline. 

-To verify if the applications works, let's go to the web-browser and enter the following URL-address and replace instance-ip with the ip of the EC2 instance that belongs to the ECS cluster : 
                           { http://instance-ip:80/simple-lamp}

![set up project](https://i.ibb.co/88JVRc6/rec.png)



-As you can see the new container is updated with the new image which holds the original containers' local data, moved with `elastio`. Also, you will find that by using `elastio` in the pipeline we ensure that logs are updated automatically in each new deployed version. All this was done with one click. 


### **Finally: using elastio in your everyday software development tasks solves critical issues and just made everything easier and more secure.**
