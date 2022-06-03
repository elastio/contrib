# Usage

## Backup

Schema of arguments:

 ```
 python elastio_stream_kafka.py backup --topic_name <Name-of-your-topic> --vault <Name-of-your-vault> --brokers <broker1> <broker2> <broker3>
 ```
    
Example:

```
python elastio_stream_kafka.py backup --topic_name MSKTEST3 --vault defl --brokers b-2.elastio-stream-backup.3udh1w.c6.kafka.us-east-2.amazonaws.com:9092 b-3.elastio-stream-backup.3udh1w.c6.kafka.us-east-2.amazonaws.com:9092 b-1.elastio-stream-backup.3udh1w.c6.kafka.us-east-2.amazonaws.com:9092
```

The backup job is based on the message offsets for each section in a topic. Data is read and stored from a Kafka topic in the original Kafka types. Then this data is saved to Elastio unchanged. For the different byte structures in a Kafka message, we have used `base64` encoding to ensure that the Kafka byte structure is not corrupted and the data is safe.

## Restore
Schema of arguments:

```
python elastio_stream_kafka.py restore --topic_name <Name-of-your-topic> --rp_id <Id-of-your-recovery-point> --brokers <broker1> <broker2> <broker3>
```
   
Example:

```
python elastio_stream_kafka.py restore --topic_name MSKTutorialTopic --rp_id rp-01g3c0cfm6mnejk5pmq4zheham --brokers b-2.elastio-stream-backup.3udh1w.c6.kafka.us-east-2.amazonaws.com:9092 b-3.elastio-stream-backup.3udh1w.c6.kafka.us-east-2.amazonaws.com:9092 b-1.elastio-stream-backup.3udh1w.c6.kafka.us-east-2.amazonaws.com:9092
```

The restore job is based on a recovery point ID. In the recovery point tags you could see interval of data in this recovery point. The tags help you to see the interval of data in recovery point.