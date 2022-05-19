import argparse
import logging
import os
import subprocess
import ast
import json
import time

from kafka import KafkaProducer


logging.basicConfig(level=logging.CRITICAL)

parser = argparse.ArgumentParser(
    prog="Elastio stream kafka",
)
subparser = parser.add_subparsers(dest="mod")

backup_parser = subparser.add_parser("backup")
backup_parser.add_argument("--topic_name", required=True, type=str, nargs="?", help="Enter Kafka topic name to backup.")
backup_parser.add_argument("--brokers", required=True, type=str, nargs="+", help="Enter one or more Kafka brokers separated by spaces.")
backup_parser.add_argument("--vault", required=True, type=str, nargs="?", help="Enter vault name.")

restore_parser = subparser.add_parser("restore")
restore_parser.add_argument("--rp_id", required=True, type=str, nargs="?", help="Enter recovery point ID.")
restore_parser.add_argument("--topic_name", required=True, type=str, nargs="?", help="Enter Kafka topic name to restore data for this topic.")
restore_parser.add_argument("--brokers", required=True, type=str, nargs="+", help="Enter one or more Kafka brokers separated by spaces.")

args = parser.parse_args()

if args.mod == "backup":
    print("Backup started.")
    res = os.popen(f"python consumer.py --topic_name {args.topic_name} --brokers {' '.join(args.brokers)} | elastio stream backup --stream-name {args.topic_name} --vault {args.vault} --output-format json").read()
    rp_info = json.loads(res)
    print(json.dumps(rp_info, indent=4))
    print(f"Status: {rp_info['status']}")
    if rp_info['status'] == 'Succeeded':
        print(f"Recovery point ID: {rp_info['data']['rp_id']}")

    with open('first_msg_info.json', 'r+') as first_msg_file:
        data = json.load(first_msg_file)
    first_msg_timestamp = data['timestamp']

    with open('last_msg_info.json', 'r+') as last_msg_file:
        data = json.load(last_msg_file)
    last_msg_timestamp = data['timestamp']
    os.system(f"elastio rp tag --rp-id {rp_info['data']['rp_id']} --tag start_timestamp={first_msg_timestamp}")
    time.sleep(1)
    os.system(f"elastio rp tag --rp-id {rp_info['data']['rp_id']} --tag end_timestamp={last_msg_timestamp}")


elif args.mod == "restore":
    print("Restore started.")
    bootstrap_servers = args.brokers
    prod = KafkaProducer(bootstrap_servers=bootstrap_servers)
    res = subprocess.run(["elastio", "stream", "restore", "--rp", args.rp_id], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    msg_count = 0
    for line in res.stdout.splitlines():
        msg = ast.literal_eval(line.decode('utf-8'))
        msg_stat = prod.send(
            topic=args.topic_name,
            key=msg['key'],
            value=json.dumps(ast.literal_eval(msg['value'])).encode('utf-8'),
            partition=msg['partition'],
            timestamp_ms=msg['timestamp']
        )
        msg_count+=1
    print("Restore finished successfuly!\nRestored messeges count: {msg_count}".format(msg_count=msg_count))
