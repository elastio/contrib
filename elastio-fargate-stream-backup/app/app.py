import os, logging
from config_file import *

logging.basicConfig(
    format='%(process)d-%(levelname)s-%(message)s',
    level=logging.INFO,
    )


def backup(bucket_name, file_key, stream_name, vault):
    status = os.system(f"python3 s3reader.py --bucket_name {bucket_name} --file_key {file_key} | elastio stream backup --stream-name {stream_name} --vault {vault}")
    logging.info(f"Task status code: {status}")


if __name__ == '__main__':
    backup(BUCKER_NAME, FILE_KEY, STREAM_NAME, VAULT)