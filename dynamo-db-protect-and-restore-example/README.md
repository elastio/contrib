# Backup DynamoDB Tables using Elastio

## Requirements
- Python 3
- Boto 3

## Installing Boto 3 on Ubuntu

```
sudo apt update
sudo apt install python3-boto3
```

## Create a DynamoDB table and write some data to it

- Create a "Music" table in Amazon DynamoDB. The table should have the following details:

    Partition key — Artist

    Sort key — SongTitle

- Create a new "Music" table using create-table as in the following AWS CLI example below:

```
aws dynamodb create-table \
    --table-name Music \
    --attribute-definitions \
        AttributeName=Artist,AttributeType=S \
        AttributeName=SongTitle,AttributeType=S \
    --key-schema \
        AttributeName=Artist,KeyType=HASH \
        AttributeName=SongTitle,KeyType=RANGE \
    --provisioned-throughput \
        ReadCapacityUnits=10,WriteCapacityUnits=5 \
    --table-class STANDARD
```
![set up project](https://i.postimg.cc/MGnM0nrv/1111.png)

## Fill the DynamoDB table with data ##

- Use the following AWS CLI example to create several new items in the "Music" table. You can do this either through the DynamoDB API or PartiQL, a SQL-compatible query language for DynamoDB:

```
aws dynamodb put-item \
    --table-name Music  \
    --item \
        '{"Artist": {"S": "No One You Know"}, "SongTitle": {"S": "Call Me Today"}, "AlbumTitle": {"S": "Somewhat Famous"}, "Awards": {"N": "1"}}'

aws dynamodb put-item \
    --table-name Music  \
    --item \
        '{"Artist": {"S": "No One You Know"}, "SongTitle": {"S": "Howdy"}, "AlbumTitle": {"S": "Somewhat Famous"}, "Awards": {"N": "2"}}'

aws dynamodb put-item \
    --table-name Music \
    --item \
        '{"Artist": {"S": "Acme Band"}, "SongTitle": {"S": "Happy Day"}, "AlbumTitle": {"S": "Songs About Life"}, "Awards": {"N": "10"} }'

aws dynamodb put-item \
    --table-name Music \
    --item \
        '{"Artist": {"S": "Acme Band"}, "SongTitle": {"S": "PartiQL Rocks"}, "AlbumTitle": {"S": "Another Album Title"}, "Awards": {"N": "8"} }'
```

## Protect and restore DynamoDB table with Elastio

Use the following [script](https://github.com/elastio/contrib/blob/master/dynamo-db-protect-and-restore-example/DynamoElastio.py) to protect and restore the "Music" table. 

Run the following command to backup the table schema and data using `elastio file backup` command in the CLI:

```
python3 DynamoElastio.py -m backup -s Music && elastio stream backup --stream-name schema.json --from-file schema.json
```

The script will create 1 file `schema.json` that will contain all the table information.

Then delete the table and run the following command to use Elastio to restore the deleted table:

```
elastio stream restore --rp rp-dg34vt9ouz4iphmo83hqxnno --to-file schema.json && python3 DynamoElastio.py -m restore -s Music --noConfirm
```

As a result you will find the table restored and ready for use.

## LICENSE

Elastio-specific modifications are Copyright 2022 Elastio Software, Inc, and are hereby released under the MIT License as was the [original work by bchew](https://github.com/bchew/dynamodump) from which this version is derived.
