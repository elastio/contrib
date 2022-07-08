import os, logging

from docker_backup_config import TOPIC_NAME, BROKERS, VAULT


logging.basicConfig(
    format='%(process)d-%(levelname)s-%(message)s',
    level=logging.INFO,
    )


def backup(topic_name: str, brokers: list, vault: str):
    logging.info(f'Topic name: {topic_name}')
    brokers = " ".join(b for b in brokers)
    logging.info(f'Brokers with join: {brokers}')
    logging.info(f'Vault: {vault}')
    status = os.system(f"python3 elastio_stream_kafka.py backup --topic_name {topic_name} --vault {vault} --brokers {brokers}")
    logging.info(f"Task status code: {status}")


if __name__ == "__main__":
    backup(
        topic_name=TOPIC_NAME,
        brokers=BROKERS,
        vault=VAULT
    )
