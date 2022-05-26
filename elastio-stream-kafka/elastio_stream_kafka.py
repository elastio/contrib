import json
import os
import argparse
import logging
import subprocess
import ast
import base64
import json

from kafka import KafkaConsumer, TopicPartition, KafkaProducer
from common import id_generator, new_message_exists


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

restore_parser = subparser.add_parser("restore")
# restore mode arguments
restore_parser.add_argument("--rp_id", required=True, type=str, nargs="?", help="Enter recovery point ID.")
restore_parser.add_argument("--topic_name", required=True, type=str, nargs="?", help="Enter Kafka topic name to restore data for this topic.")
restore_parser.add_argument("--brokers", required=True, type=str, nargs="+", help="Enter one or more Kafka brokers separated by spaces.")

args = parser.parse_args()

if args.mod == "backup":
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
        api_version=(0, 10, 1)
    )

    topic_previously_backed_up = False
    res = subprocess.run(
        ['elastio', 'rp', 'list', '--output-format', 'json', '--type', 'stream'],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
    rps = [json.loads(rp) for rp in res.stdout.splitlines()]
    for rp in rps[0]:
        if rp['kind']['kind'] == 'Stream':
            rp_name = rp['asset_snaps'][0]['asset_id'].split(':')[-1]
            try:
                if rp_name == args.topic_name and rp['tags']['topic_name'] == args.topic_name:
                    topic_previously_backed_up = True
                    break
            except KeyError:
                continue

    print(f"Topic previously backed up: {topic_previously_backed_up}")

    partitions = consumer.partitions_for_topic(topic_name)
    partition_count = len(partitions)
    topic_info_data['partition_count'] = partition_count
    new_message_info = {}
    for partition in partitions:
        if topic_previously_backed_up:
            _key = f'partition_{str(partition)}_last_msg_offset'
            new_message_info[partition] = new_message_exists(topic_name, bootstrap_servers, partition, int(rp['tags'][_key])+1)
        else:
            new_message_info[partition] = new_message_exists(topic_name, bootstrap_servers, partition, 0)

    if True in new_message_info.values():
        print(f"Elastio starting backup {args.topic_name} topic.")
        override_hostname = "{cluster_name}:{topic_name}".format(
                cluster_name=str(args.brokers[0].split('.')[1]),
                topic_name=args.topic_name
                )
        proc = subprocess.Popen(
            ['elastio', 'stream', 'backup', '--stream-name', topic_name, '--output-format', 'json', '--hostname-override', override_hostname, '--vault', args.vault],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
        if topic_previously_backed_up:
            for partition_key in new_message_info.keys():
                first_message = True
                if new_message_info[partition_key]:
                    consumer.assign([TopicPartition(topic_name, partition_key), ])
                    for msg in consumer:
                        _key = f'partition_{str(partition_key)}_last_msg_offset'
                        if msg.offset > int(rp['tags'][_key]):
                            if first_message:
                                topic_info_data[f'partition_{str(partition_key)}_first_msg_offset'] = msg.offset
                                topic_info_data[f'partition_{str(partition_key)}_first_msg_timestamp'] = msg.timestamp
                                first_message = False
                            data = json.dumps({
                                "topic": msg.topic,
                                "key": base64.b64encode(msg.key).decode(),
                                "value": base64.b64encode(msg.value).decode(),
                                "partition": msg.partition,
                                "timestamp": msg.timestamp,
                                "offset": msg.offset
                            }).encode()
                            proc.stdin.write(data)
                            proc.stdin.write(b'\n')
                            topic_info_data[f'partition_{str(partition_key)}_last_msg_offset'] = msg.offset
                            topic_info_data[f'partition_{str(partition_key)}_last_msg_timestamp'] = msg.timestamp
                else:
                    _key = f'partition_{str(partition_key)}_last_msg_offset'
                    topic_info_data[f'partition_{str(partition_key)}_last_msg_offset'] = int(rp['tags'][_key])
                    topic_info_data[f'partition_{str(partition_key)}_last_msg_timestamp'] = 0
        else:
            for partition_key in new_message_info.keys():
                first_message = True
                if new_message_info[partition_key]:
                    consumer.assign([TopicPartition(topic_name, partition_key), ])
                    for msg in consumer:
                        if first_message:
                            topic_info_data[f'partition_{str(partition_key)}_first_msg_offset'] = msg.offset
                            topic_info_data[f'partition_{str(partition_key)}_first_msg_timestamp'] = msg.timestamp
                            first_message = False
                        data = json.dumps({
                            "topic": msg.topic,
                            "key": base64.b64encode(msg.key).decode(),
                            "value": base64.b64encode(msg.value).decode(),
                            "partition": msg.partition,
                            "timestamp": msg.timestamp,
                            "offset": msg.offset
                        }).encode()
                        proc.stdin.write(data)
                        proc.stdin.write(b'\n')
                        topic_info_data[f'partition_{str(partition_key)}_last_msg_offset'] = msg.offset
                        topic_info_data[f'partition_{str(partition_key)}_last_msg_timestamp'] = msg.timestamp
                else:
                    topic_info_data[f'partition_{str(partition_key)}_last_msg_offset'] = 0
                    topic_info_data[f'partition_{str(partition_key)}_last_msg_timestamp'] = 0

        proc.stdin.close()
        proc.wait()
        result = proc.stdout.read().decode()
        rp_info = json.loads(result)
        print(json.dumps(rp_info, indent=4))
        print(f"Status: {rp_info['status']}")
        if rp_info['status'] == 'Succeeded':
            print(f"Recovery point ID: {rp_info['data']['rp_id']}")
            for _key, _value in topic_info_data.items():
                os.system(f"elastio rp tag --rp-id {rp_info['data']['rp_id']} --tag {_key}={_value}")

    else:
        print("You don't have new message to backup")
    consumer.close()

elif args.mod == "restore":
    print(f"Elastio starting restore.\nRecovery point ID: {args.rp_id}")
    bootstrap_servers = args.brokers
    prod = KafkaProducer(bootstrap_servers=bootstrap_servers, api_version=(0, 10, 1))
    res = subprocess.run(
        ["elastio", "stream", "restore", "--rp", args.rp_id],
        stdout=subprocess.PIPE)
    msg_count = 0
    datas = (json.loads(line.decode()) for line in res.stdout.splitlines())
    for data in datas:
        msg_stat = prod.send(
            topic=data['topic'],
            key=base64.b64decode(data['key']),
            value=base64.b64decode(data['value']),
            partition=data['partition'],
            timestamp_ms=data['timestamp']
        )
        msg_count+=1
    prod.close()
    print("Restore finished successfuly!\nRestored messeges count: {msg_count}".format(msg_count=msg_count))
