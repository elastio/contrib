import json
import os
import argparse
import logging
import subprocess

from kafka import KafkaConsumer, TopicPartition
from common import id_generator, write_topic_info


logging.basicConfig(level=logging.CRITICAL)

backup_parser = argparse.ArgumentParser(
    prog="Elastio stream kafka consumer"
)
backup_parser.add_argument("--topic_name", type=str, nargs="?", help="Enter Kafka topic name to backup.")
backup_parser.add_argument("--brokers", type=str, nargs="+", help="Enter one or more Kafka brokers separated by spaces.")
backup_parser.add_argument("--stream_name", type=str, nargs="?", help="Enter stream name of backup.")
args = backup_parser.parse_args()

# parse brokers and topic name from the script arguments
bootstrap_servers = args.brokers
topic_name = args.topic_name
_id = id_generator()
topic_info_data = {}
topic_info_data['topic_name'] = args.topic_name

consumer = KafkaConsumer(
    group_id=f'{_id}-group',
    bootstrap_servers=bootstrap_servers,
    auto_offset_reset='earliest', # latest/earliest
    enable_auto_commit=True,
    auto_commit_interval_ms=1000, # 1s 
    consumer_timeout_ms=10000, # 10s
    api_version=(2,0,2)
    )

res = subprocess.run(
    ['elastio', 'rp', 'list', '--output-format', 'json', '--type', 'stream'],
    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
    )
topic_previously_backed_up = False
rps = [json.loads(rp) for rp in res.stdout.splitlines()]
for rp in rps[0]:
    if rp['kind']['kind'] == 'Stream':
        rp_name = rp['asset_snaps'][0]['asset_id'].split(':')[-1]
        try:
            if rp_name == args.stream_name and rp['tags']['topic_name'] == args.topic_name:
                topic_previously_backed_up = True
                break
        except KeyError:
            break

partition_count = len(consumer.partitions_for_topic(topic_name))
topic_info_data['partition_count'] = partition_count
if topic_previously_backed_up:
    for partition in range(partition_count):
        first_message = True
        consumer.assign([TopicPartition(args.topic_name, partition),])
        for msg in consumer:
            if msg.offset > int(rp['tags'][f'partition_{str(partition)}_last_msg_offset']):
                # print(msg)
                if first_message:
                    topic_info_data[f'partition_{str(partition)}_first_msg_offset'] = msg.offset
                    first_message = False
                print({"topic": msg.topic, "key": msg.key, "value": msg.value, "partition": msg.partition, "timestamp": msg.timestamp, "offset": msg.offset, "headers":msg.headers})
            topic_info_data[f'partition_{str(partition)}_last_msg_offset'] = msg.offset
    write_topic_info(data=topic_info_data)
else:
    for partition in range(partition_count):
        first_message = True
        consumer.assign([TopicPartition(args.topic_name, partition),])
        for msg in consumer:
            # print(msg)
            if first_message:
                topic_info_data[f'partition_{str(partition)}_first_msg_offset'] = msg.offset
                first_message = False
            print({"topic": msg.topic, "key": msg.key, "value": msg.value, "partition": msg.partition, "timestamp": msg.timestamp, "offset": msg.offset, "headers":msg.headers})
        topic_info_data[f'partition_{str(partition)}_last_msg_offset'] = msg.offset
    write_topic_info(data=topic_info_data)

consumer.close()
