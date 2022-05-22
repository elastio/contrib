import string
import random
import json
import os


def id_generator(size=6, chars=string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def write_topic_info(data):
    with open('topic_info.json', 'w+') as topic_info_file:
        json.dump(data, topic_info_file, indent=4)


def read_topic_info():
    with open('topic_info.json', 'r+') as topic_info_file:
        data = json.load(topic_info_file)
    return data


def delete_topic_info():
    os.remove('topic_info.json')
