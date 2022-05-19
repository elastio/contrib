from kafka import KafkaConsumer
import json
import os
import argparse
import logging
logging.basicConfig(level=logging.CRITICAL)

backup_parser = argparse.ArgumentParser(
    prog="Elastio stream kafka consumer"
)
backup_parser.add_argument("--topic_name", type=str, nargs="?", help="Enter Kafka topic name to backup.")
backup_parser.add_argument("--brokers", type=str, nargs="+", help="Enter one or more Kafka brokers separated by spaces.")
args = backup_parser.parse_args()
bootstrap_servers = args.brokers
topic_name = args.topic_name


consumer = KafkaConsumer(
    topic_name,
    group_id='elastio-group',
    bootstrap_servers=bootstrap_servers,
    auto_offset_reset='earliest', # latest/earliest
    enable_auto_commit=True,
    auto_commit_interval_ms=1000, # 1s 
    consumer_timeout_ms=10000, # 10s
    api_version=(2,0,2)
    )

if os.path.exists('last_msg_info.json'):
    with open('last_msg_info.json', 'r+') as last_msg_file:
        data = json.load(last_msg_file)
    if data['topic'] == args.topic_name:
        for msg in consumer:
            if msg.timestamp > data['timestamp']:
                # print(msg)
                print({"topic": msg.topic, "key": msg.key, "value": msg.value.decode('utf-8'), "partition": msg.partition, "timestamp": msg.timestamp})
    else:
        for msg in consumer:
            # print(msg)
            print({"topic": msg.topic, "key": msg.key, "value": msg.value.decode('utf-8'), "partition": msg.partition, "timestamp": msg.timestamp})
else:
    for msg in consumer:
        # print(msg)
        print({"topic": msg.topic, "key": msg.key, "value": msg.value.decode('utf-8'), "partition": msg.partition, "timestamp": msg.timestamp})
try:
    lmsg_topic = msg.topic
    lmsg_key = msg.key
    lmsg_timestamp = msg.timestamp
    lmsg_offset = msg.offset
    lmsg_value = msg.value.decode('utf-8')
    consumer.close()
    data = {
        'topic': lmsg_topic,
        'offset': lmsg_offset,
        'timestamp': lmsg_timestamp,
        'key': lmsg_key,
        'value': lmsg_value
        }
    with open('last_msg_info.json', 'w+') as last_msg_file:
        json.dump(data, last_msg_file, indent=4)
except NameError:
    print("You don't have new messges to backup.")
