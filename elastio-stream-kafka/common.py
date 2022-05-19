import string
import random
import json


def id_generator(size=6, chars=string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def store_last_message(msg):
    try:
        lmsg_topic = msg.topic
        lmsg_key = msg.key
        lmsg_timestamp = msg.timestamp
        lmsg_offset = msg.offset
        lmsg_value = msg.value.decode('utf-8')

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


def store_first_message(msg, fmsg=True):
    if fmsg:
        try:
            fmsg_topic = msg.topic
            fmsg_key = msg.key
            fmsg_timestamp = msg.timestamp
            fmsg_offset = msg.offset
            fmsg_value = msg.value.decode('utf-8')
            
            data = {
                'topic': fmsg_topic,
                'offset': fmsg_offset,
                'timestamp': fmsg_timestamp,
                'key': fmsg_key,
                'value': fmsg_value
                }
            with open('first_msg_info.json', 'w+') as last_msg_file:
                json.dump(data, last_msg_file, indent=4)
        except NameError:
            print("You don't have new messges to backup.")
