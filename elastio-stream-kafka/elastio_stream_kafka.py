import argparse
import logging
import os
import subprocess
import ast
import json
import time

from kafka import KafkaProducer
from common import read_topic_info, delete_topic_info


logging.basicConfig(level=logging.CRITICAL)

parser = argparse.ArgumentParser(
    prog="Elastio stream kafka",
)
subparser = parser.add_subparsers(dest="mod")
# subparser accept two posible modes of work this script backup and restore

backup_parser = subparser.add_parser("backup")
# backup mode arguments
backup_parser.add_argument("--topic_name", required=True, type=str, nargs="?", help="Enter Kafka topic name to backup.")
backup_parser.add_argument("--brokers", required=True, type=str, nargs="+", help="Enter one or more Kafka brokers separated by spaces.")
backup_parser.add_argument("--vault", required=True, type=str, nargs="?", help="Enter vault name.")
backup_parser.add_argument("--stream_name", required=True, type=str, nargs="?", help="Enter name of the stream.")

restore_parser = subparser.add_parser("restore")
# restore mode arguments
restore_parser.add_argument("--rp_id", required=True, type=str, nargs="?", help="Enter recovery point ID.")
restore_parser.add_argument("--topic_name", required=True, type=str, nargs="?", help="Enter Kafka topic name to restore data for this topic.")
restore_parser.add_argument("--brokers", required=True, type=str, nargs="+", help="Enter one or more Kafka brokers separated by spaces.")

args = parser.parse_args()

if args.mod == "backup":
    print("Backup started.")
    res = os.popen(f"python consumer.py --topic_name {args.topic_name} --brokers {' '.join(args.brokers)} --stream_name {args.stream_name} | elastio stream backup --stream-name {args.stream_name} --vault {args.vault} --output-format json").read()
    rp_info = json.loads(res)
    print(json.dumps(rp_info, indent=4))
    print(f"Status: {rp_info['status']}")
    if rp_info['status'] == 'Succeeded':
        print(f"Recovery point ID: {rp_info['data']['rp_id']}")
    topic_info_data = read_topic_info()
    os.system(f"elastio rp tag --rp-id {rp_info['data']['rp_id']} --tag topic_name={topic_info_data['topic_name']}")
    time.sleep(1)
    os.system(f"elastio rp tag --rp-id {rp_info['data']['rp_id']} --tag partition_count={topic_info_data['partition_count']}")
    time.sleep(1)
    for partition in range(topic_info_data['partition_count']):
        first_key = 'partition_' + str(partition) + '_first_msg_offset'
        second_key = 'partition_' + str(partition) + '_last_msg_offset'
        os.system(f"elastio rp tag --rp-id {rp_info['data']['rp_id']} --tag partition_{str(partition)}_first_msg_offset={topic_info_data[first_key]}")
        time.sleep(1)
        os.system(f"elastio rp tag --rp-id {rp_info['data']['rp_id']} --tag partition_{str(partition)}_last_msg_offset={topic_info_data[second_key]}")
        time.sleep(1)
    delete_topic_info()

elif args.mod == "restore":
    print("Restore started.")
    bootstrap_servers = args.brokers
    prod = KafkaProducer(bootstrap_servers=bootstrap_servers)
    res = subprocess.run(
        ["elastio", "stream", "restore", "--rp", args.rp_id],
        stdout=subprocess.PIPE)
    msg_count = 0
    for line in res.stdout.splitlines():
        msg = ast.literal_eval(line.decode())
        msg_stat = prod.send(
            topic=args.topic_name,
            key=msg['key'],
            value=msg['value'],
            partition=msg['partition'],
            timestamp_ms=msg['timestamp'],
            headers=msg['headers']
        )
        msg_count+=1
    prod.close()
    print("Restore finished successfuly!\nRestored messeges count: {msg_count}".format(msg_count=msg_count))
