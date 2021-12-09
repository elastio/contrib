# Migrate a PostgreSQL Database From One Environment to Another Using Elastio

A common problem, slowing down the SDLC (Software Development Life Cycles, occurs when the databases in the different environments (dev, qa, staging, and prod) are not in sync. And, without an automated process of sorts, DBAs will battle to ensure that every environment's databases are always synchronized. 

To solve this challenge, our [Elastio Backup and Restore Database](https://docs.elastio.com/src/backup-restore/backup-databases.html){:target="_blank"} feature saves developers, DBAs, and DevOps Engineers a lot of manual work by automating the database migration function. 

**Note:** Elastio can migrate different databases. For more inforrmation on this topic, visit [docs.elastio.com/src/backup-restore/backup-databases.html](https://docs.elastio.com/src/backup-restore/backup-databases.html){:target="_blank"} 

## How to migrate a PostgreSQL database between two environments: An example

We will use a standard web application developed using Python, Flask, and PostgreSQL to demonstrate this concept. 

This step-by-step guide demonstrates the end-to-end database migration pipeline, including prerequisite requirements, installation, and how to use the Elastio Backup and Restore Database feature. 

### Step 1: Requirements

The following prerequisites are necessary before continuing with the process: 

- 2 database instances (production and test)
- 1 standard instance or environment (production) to deploy the software application to

### Step 2: Installation

- Download this project to your test environment from this [link](https://www.dropbox.com/s/14gdqj78810udln/IndexedSearchPythonDocker.zip?dl=0){:target="_blank"}
- Install Docker on your test instance
- Download and install PostgreSQL on both the database instances, if you don't already have PostgreSQL installed
- Install Elastio on both database instances and the production server 

**Note:** For steps on how to install the Elastio CLI, visit [docs.elastio.com/src/getting-started/install-cli](https://docs.elastio.com/src/getting-started/install-cli.html){:target="_blank"}

### Step 3: Using Elastio 

As per our example, the first thing to do is to create the phonebook database and import the data on the test DB instance. 

**Note:** Because this example describes how to use Elastio's Database Backup and Restore function, the test data has to be set up, even though, operationally, these databases must be kept in sync across all environments. 

1. After successfully installing the PostgreSQL database server, copy the phone_book.sql file to your chosen path on your DB instance. In our case it is: `/home/ubuntu/postgres`

2. To create a database and import the phone_book.sql file, you must follow this step-by-step guide:
   
   1. Run the following command to log into the PostgreSQL interactive terminal program: 
      ```
      sudo -i -u postgres psql 
      ```
      Enter your password if prompted to do so. 

   2. Type in the following SQL statement to create the new phonebook database (and press \<enter>):
      ```
      CREATE DATABASE phonebook;
      ```

   3. Run the following SQL command to import the phone_book.sql file:
      ```
      postgres -f <file path>/phone_book.sql phonebook
      ```
\#### This command isn't importing the phone_book.sql file - either the command is wrong or the sql file isn't correct. 

   4. To confirm whether the phonebook database was created, select the phonebook database by running the following command: 
      ```
      \l 
      ```
      The output should be as follows: 

      ![image](images/postgresql-output.png)

   5. To confirm whether the data was imported into the phonebook database, run the following commands: 
      ```
      \c phonebook
      ```   
      and then 
      ```
      \dt
      ```
      This command should return the following output:
 
      ![image][images/list-db-tables.png]
      
### Step 4: Building and deploying an indexed web search application

After you've successfully installed the PostgreSQL database server, created a database, and imported the phonebook data on test, the next step is to build and deploy your indexed search web app. Here is a list of steps to follow to achieve this outcome: 

1. Edit the following line in the eg_phonebook.py file with your production PostgreSQL credentials: 
   ```
   conn=psycopg2.connect(database="phonebook", user="postgres", host="172.17.0.2", password="12345")
   ```

2. Create a Docker file as follows:
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

3. Make sure that the following files have been added to your web application directory: eg_phonebook.py,index.html,phone_book.sql,requirements.txt. Navigate to this directory and then run the following command to build your web application in a Docker container: 
   ```
   docker build -t eg_phonebook .
   ```
\#### please confirm that this line of code is correct

4. Use the following command to run the application:
   ```
   docker run -p 0.0.0.0:80:80 -d eg_phonebook
   ```

5. To verify that your web app works, go to your web browser and enter the following URL: 
   **Note:** Replace <\instance-ip> with your web application's IP address. 
   ```
   http://<instance-ip>:80
   ```

   ![set up project](https://i.ibb.co/GxX96Xg/vor.png)

   As you can see from the above screenshot, the web application has started and is functional.

 ## Using Elastio to migrate data between two or more instances

 Using Elastio to migrate data between two or more environments is a primarily automated and effortless process. Here is a step-by-step guide to migrate data between test and production:

1. Navigate to the DB instance that you want to migrate from

2. Run the following command to back up the phonebook DB, adding the tag postgres:phonebook: 
   ```
   pg_dump postgres  | elastio stream backup --stream-name phonebook  --tag postgres:phonebook
   ```

3. Navigate to your production instance that you want to migrate the phonebook database to 
   
4. Restore this database that you used Elastio to back up in the previous step, using the following command:
   ```
   elastio stream restore --rp '@{2021-12-05 15:05:51}'  --host aee5f2b441c8  | psql
   ```
5. Lastly, open your web browser and navigate to the web app's URL on production to verify that the app is working (See the image below).
   **Note:** Replace <\instance-ip> with your web application's IP address. 
   ```
   http://<instance-ip>:80
   ``` 

![set up project](https://www.codeproject.com/KB/applications/1257203/step38_amilinux.png)

This image demonstrates that you successfully migrated the phonebook database to the production database instance using Elastio's powerful backup-as-code feature. Therefore, using Elastio as part of your software development lifecycle and CI pipelines increases your operational efficiencies and application security. 



