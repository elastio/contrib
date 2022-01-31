import os, logging
from config_file import *

logging.basicConfig(
    format='%(process)d-%(levelname)s-%(message)s',
    level=logging.INFO,
    )


def backup(bucket_name, file_key, stream_name, vault):
    logging.info("Stream backup from s3 will start.")
    logging.info("Bucket name: %s" % bucket_name)
    logging.info("File key: %s" % file_key)
    logging.info("Stream name: %s" % stream_name)
    logging.info("Vault name: %s" % vault)
    status = os.system(f"python3 s3reader.py --bucket_name {bucket_name} --file_key {file_key} | elastio stream backup --stream-name {stream_name} --vault {vault}")
    logging.info(f"Task status code: {status}")


if __name__ == '__main__':
    backup(BUCKER_NAME, FILE_KEY, STREAM_NAME, VAULT)