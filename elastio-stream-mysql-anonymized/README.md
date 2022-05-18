# MySQL Anonymized via Myanon and Elastio

### Author: Robert Saylor - customphpdesign@gmail.com

---

## Requirements
- MySQL Database
- [Myanon](https://ppomes.github.io/myanon/)
- Elastio

## Assumptions

You have a MySQL database setup, AWS CLI and Elastio installed on Ubuntu 20.04.

Note: Myanon supports other Linux operating systems as well as Elastio.

## Installing Myanon

Visit the github page for [myanon](https://github.com/ppomes/myanon) that has detailed installation instructions for the Linux operating system you are using. This document will explain the steps on Ubuntu 20.04

```
git clone git@github.com:ppomes/myanon.git
cd myanon
sudo apt-get install autoconf automake flex bison build-essential
sudo apt-get install build-essential
./autogen.sh
./configure
make
make install
```

## Database example

```
CREATE TABLE `contacts` (
  `id` int NOT NULL AUTO_INCREMENT,
  `first` varchar(200) NOT NULL,
  `last` varchar(200) NOT NULL,
  `email` varchar(200) NOT NULL,
  `mobile` varchar(200) NOT NULL,
  `address` varchar(200) NOT NULL,
  `city` varchar(200) NOT NULL,
  `state` varchar(200) NOT NULL,
  `zip` varchar(200) NOT NULL,
  `dob` date NOT NULL,
  `ssn` varchar(200) NOT NULL,
  `date_created` date NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb3;
```

## Example elastio.cnf

```
secret = 'mysecret'
stats = 'no'

tables = {
    `contacts` = {
        `first` = texthash 9
        `last` = texthash 9
        `email` = emailhash 'example.com' 12
        `ssn` = inthash 9
        `dob` = fixed '1970-01-01'
    }
}
```

## Running the script

```
bash mysql-anonymized-data.sh DATABASE_NAME BACKUP_FILE_NAME
```

> Parameters:
- Replace "DATABASE_NAME" with the name of your database.
- Replace "BACKUP_FILE_NAME" with the file name you would like stored in the Elastio vault. IE: database-backup.sql

## Expected results

The fields first, last, email, ssn and dob data would be replaced in the Elastio vault with hashed values according to the myanon config file.

## Example in action

View the [video](https://asciinema.org/a/qKERwE1jn2EBnhIzZKw88ENpZ) that showcases the script.
