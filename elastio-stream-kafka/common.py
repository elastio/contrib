import string
import random
import json
import os

from kafka import KafkaConsumer, TopicPartition


def id_generator(size=6, chars=string.ascii_lowercase + string.digits) -> str:
    """Generating random strings with specified size"""
    return ''.join(random.choice(chars) for _ in range(size))


def new_message_exists(topic: str, bootstrap_servers: list, partition: int, offset: int) -> dict:
    """
    Check Kafka topic partition for new message.
    Function connect to Kafka, read message for the specified partition.
    Check message offset compares with the specified offset
    Returns True if the message offset is 2 greater than the specified offset.
    Otherwise returns False. 
    """
    _id = id_generator()
    consumer = KafkaConsumer(
        group_id=f'{_id}-group',
        bootstrap_servers=bootstrap_servers,
        auto_offset_reset='earliest', # latest/earliest
        enable_auto_commit=True,
        auto_commit_interval_ms=1000, # 1s 
        consumer_timeout_ms=10000, # 10s
        api_version=(0, 10, 1)
    )
    new_message_info = {}
    minimal_new_message_count_to_backup = 2 # first and last
    new_message_count = 0
    consumer.assign([TopicPartition(topic, partition), ])
    print(f"Checking for new message - Topic: {topic} | Partition {partition}")
    for msg in consumer:
        if msg.offset >= offset:
            new_message_count+=1
            if new_message_count >= minimal_new_message_count_to_backup:
                consumer.close()
                return True
            else:
                continue
    consumer.close()
    return False
