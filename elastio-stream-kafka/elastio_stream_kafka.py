import argparse
import logging
import os
import subprocess
import ast
import json

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
    status = os.system(f"python consumer.py --topic_name {args.topic_name} --brokers {' '.join(args.brokers)} | elastio stream backup --stream-name {args.topic_name} --vault {args.vault}")
    if status == 0:
        print('Backup finished successfuly!')
    else:
        print('Status code: {}'.format(status))

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