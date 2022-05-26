import string
import random
import json
import os

from kafka import KafkaConsumer, TopicPartition


def id_generator(size=6, chars=string.ascii_lowercase + string.digits) -> str:
    return ''.join(random.choice(chars) for _ in range(size))


def new_message_exists(topic: str, bootstrap_servers: list, partition: int, offset: int) -> dict:
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
    print(f"Topic: {topic} | Partition {partition}")
    for msg in consumer:
        # if topic_previously_backed_up:
        #     if msg.offset > offset:
        #         print(f"msg-offset: {msg.offset} | offset: {offset}")
        #         new_message_count+=1
        #         if new_message_count > minimal_new_message_count_to_backup:
        #             consumer.close()
        #             return True
        #             # break
        #         else:
        #             continue
        # else:
        if msg.offset >= offset:
            print(f"msg-offset: {msg.offset} | offset: {offset}")
            new_message_count+=1
            if new_message_count >= minimal_new_message_count_to_backup:
                consumer.close()
                return True
                # break
            else:
                continue
    consumer.close()
    return False
