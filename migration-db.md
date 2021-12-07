# Migrate Postgres Database from one environment to another using Elastio
## **Problem:-**
## A common problem that slow down the software development cycle is that when  the developers developing the project they are working on the dev environment and then they migrate there work to staging or prod environment but when it comes to the database it becomes a hasling task for the database admin to make sure that everything is in sink all the time    
## **Solution:-**
## using elastio can spare both the devolpers and the (database admins, devops engineers) alot of manual work.  
 \* elastio spport different databases you can visit 
 https://docs.elastio.com/src/backup-restore/backup-databases.html to learn more

-------
 # we will use A Standard Web-Application Created By Using Python, Flask and PostgreSQL
 ### Requirements
* 2 DB instances {production,testing}
* 1 normal instance to deploy project on {production}
### Install
1. Download this project in your instance from this link https://www.dropbox.com/s/14gdqj78810udln/IndexedSearchPythonDocker.zip?dl=0
2. install docker on the instance
3. install postgressql on the db instances
4. install elastio on both databases and production server 

##### \*for steps on how to install elastio visit https://docs.elastio.com/src/getting-started/install-cli.html 

### usage
### Step 1: Phonebook PostgreSQL Database Maintenence Steps:

**[in the testing DB instance]**

-After we've successfully setup the PostgreSQL database server , we must import a ready-to-use database to the PostgreSQL server. To make the example simple ,we must copy the phone_book.sql file to the disierd path in my case its ``/home/ubuntu/postgres ``

-To import the existing database, we have to enter the following two commands:
`` 
   psql -U postgres
``

-and then type in this sql-statement, after which the new phonebook database is created.

``
  CREATE DATABASE phonebook;
``

After entering this command, the phone_book.sql dump file is successfully imported to the newly created phonebook database
 ###### \*Note: we will do the command below only in the dev DB to se what elastio is capble of in the migration process 

``
  psql -U postgres -f /home/ubuntu/postgres/phone_book.sql phonebook
``

-then the database for the development environment is ready.

### Step 2: Building And Running Indexed Search Web Application.

**[in the production instance]**

-After we've successfully maintained the PostgreSQL database server and imported the phonebook database with data, now, let's build and deploy our indexed search web-application. First what we have to do is to create an appropriate Docker file as follows:
 ###### \* Note: before creating the image go to  the file ``eg_phonebook.py`` and edit the line ``conn=psycopg2.connect(database="phonebook", user="postgres", host="172.17.0.2", password="12345")`` with your production postgresql creds


```

    FROM ubuntu:18.04
    WORKDIR /app
    COPY . /app
    RUN apt-get update -y && \
	    apt-get install -y python3-pip python-pip python3-dev software-properties-common
    RUN pip install  -r requirements.txt 
    CMD [ "python3", "/app/eg_phonebook.py" ]
    EXPOSE 80

```


Finally, after the Docker file has been created and the files  ``eg_phonebook.py,index.html,phone_book.sql,requirements.txt`` are present in the path ``/home/ubuntu/project`` we must enter the following commands to build our eg_phonebook web-application:

``
  docker build -t eg_phonebook .
``

To run the application we will use the following command:

``
  docker run -p 0.0.0.0:80:80 -d eg_phonebook
``

-To verify if the applications works as just fine, let's go to the web-browser and enter the following URL-address and replace instance-ip with your ip :
                           { http://instance-ip:80}

![set up project](https://i.ibb.co/GxX96Xg/vor.png)

As you can see at the figure above the following web-application has started and is ready to work but because our production DB ``phonebook`` is empty we get no results .

 ## -using elastio to migrate from dev DB to Prod DB effortlessly and without much manual work

 ### Step 1: Go to the Dev DB instance that we want to migrate from :
 ### Step 2: Backup the ``phonebook`` DB and give it a tag postgres:phonebook  with the command:
 ``pg_dump postgres  | elastio stream backup --stream-name phonebook  --tag postgres:phonebook``
 ### Step 3: Go to the prod DB instance that we want to migrate to and restore the ``phonebook`` DB which we backed up earlier with the command:
 ``elastio stream restore --rp '@{2021-12-05 15:05:51}'  --host aee5f2b441c8  | psql``

-let's go to the web-browser and refresh the  URL-address of the production instance and see the magic : { http://instance-ip:80}


![set up project](https://www.codeproject.com/KB/applications/1257203/step38_amilinux.png)

-As we can see at the figure above the ``phonebook`` database is migrated to the production database instance with no need for alot of unnessasry hassling manual work  by using elastio's powerful backup as code approach 


### **Finally: As we saw using elastio in your everyday software development tasks just made everything easier and more secure.**

