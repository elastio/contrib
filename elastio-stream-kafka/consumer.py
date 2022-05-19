import json
import os
import argparse
import logging
import subprocess

from kafka import KafkaConsumer
from common import id_generator, store_last_message, store_first_message


logging.basicConfig(level=logging.CRITICAL)

backup_parser = argparse.ArgumentParser(
    prog="Elastio stream kafka consumer"
)
backup_parser.add_argument("--topic_name", type=str, nargs="?", help="Enter Kafka topic name to backup.")
backup_parser.add_argument("--brokers", type=str, nargs="+", help="Enter one or more Kafka brokers separated by spaces.")
args = backup_parser.parse_args()

# parse brokers and topic name from the script arguments
bootstrap_servers = args.brokers
topic_name = args.topic_name
_id = id_generator()

consumer = KafkaConsumer(
    topic_name,
    group_id=f'{_id}-group',
    bootstrap_servers=bootstrap_servers,
    auto_offset_reset='earliest', # latest/earliest
    enable_auto_commit=True,
    auto_commit_interval_ms=1000, # 1s 
    consumer_timeout_ms=10000, # 10s
    api_version=(2,0,2)
    )

res = subprocess.run(
    ['elastio', 'rp', 'list', '--output-format', 'json'],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
topic_already_exists = False
rps = [json.loads(rp) for rp in res.stdout.splitlines()]
for rp in rps[0]:
    if rp['kind']['kind'] == 'Stream':
        rp_name = rp['asset_snaps'][0]['asset_id'].split(':')[-1]
        if rp_name == args.topic_name:
            try:
                end_timestamp = rp['tags']['end_timestamp']
                topic_already_exists = True
                break
            except KeyError:
                break

fmsg = True
if topic_already_exists:
    for msg in consumer:
        if msg.timestamp > int(end_timestamp):
            # print(msg)
            if fmsg:
                store_first_message(msg, fmsg=fmsg)
                fmsg = False
            print({"topic": msg.topic, "key": msg.key, "value": msg.value, "partition": msg.partition, "timestamp": msg.timestamp})
    store_last_message(msg=msg)
else:
    for msg in consumer:
        # print(msg)
        if fmsg:
            store_first_message(msg, fmsg=fmsg)
            fmsg = False
        print({"topic": msg.topic, "key": msg.key, "value": msg.value, "partition": msg.partition, "timestamp": msg.timestamp})
    store_last_message(msg=msg)

consumer.close()
