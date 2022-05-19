import string
import random
import json
import sys


def id_generator(size=6, chars=string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def store_last_message(msg):
    try:
        lmsg_timestamp = msg.timestamp
        data = {
            'timestamp': lmsg_timestamp
            }
        with open('last_msg_info.json', 'w+') as last_msg_file:
            json.dump(data, last_msg_file, indent=4)
    except NameError:
        print("You don't have new messges to backup.", file=sys.stderr)


def store_first_message(msg, fmsg=True):
    if fmsg:
        try:
            fmsg_timestamp = msg.timestamp
            data = {
                'timestamp': fmsg_timestamp
                }
            with open('first_msg_info.json', 'w+') as last_msg_file:
                json.dump(data, last_msg_file, indent=4)
        except NameError:
            print("You don't have new messges to backup.", file=sys.stderr)
