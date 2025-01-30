#!/usr/bin/env python3

import argparse
import asyncio
import json
import logging
import signal
import sys

from contextlib import AsyncExitStack
from dataclasses import asdict, is_dataclass
from datetime import datetime
import time
from typing import TYPE_CHECKING

__version__ = '0.33.0'

if TYPE_CHECKING:
    from types_aiobotocore_ec2 import EC2Client
    from types_aiobotocore_efs import EFSClient
    from types_aiobotocore_fsx import FSxClient
    from types_aiobotocore_organizations import OrganizationsClient
    from types_aiobotocore_s3 import S3Client
    from types_aiobotocore_sts import STSClient

GREEN = "\033[0;32m"
RED = "\033[0;31m"
YELLOW = "\033[0;33m"
BLACK = "\033[0;30m"
BLUE = "\033[0;34m"

RESET = "\033[0m"
BOLD = "\033[1m"

try:
    import aiobotocore.session
except ImportError as err:
    print(
        f"{RED}Import error: {err}{RESET}\n"
        "Install the dependencies with this command:\n"
        f"{GREEN}pip3 install --upgrade aiobotocore{RESET}"
    )
    sys.exit(1)

#########################
### Arguments parsing ###
#########################

arg_parser = argparse.ArgumentParser(
    description=f"Inventory collector (v{__version__}) collects inventory data from "
        "the given AWS accounts, shows the summary of inventory volume and saves the full info "
        "into a CSV file.",
)

auth_group = arg_parser.add_argument_group(f"{GREEN}{BOLD}Auth{RESET}")
auth_group.add_argument(
    "--assume-role",
    help = "Name of the IAM role to assume in the processed accounts (default: %(default)s)",
    default = 'OrganizationAccountAccessRole'
)

accs_group = arg_parser.add_argument_group(
    title=f"{GREEN}{BOLD}Accounts selection{RESET}",
    description=f"({BOLD}default{RESET}: current account only)"
)
accs_exclusive_group = accs_group.add_mutually_exclusive_group()

accs_exclusive_group.add_argument(
    "--accounts",
    nargs="+",
    help="Space-separated list of AWS account IDs to collect inventory from",
)

accs_exclusive_group.add_argument(
    "--all-accounts",
    action="store_true",
    help="Discover all accounts in the organization, and collect inventory from all of them",
)

accs_group.add_argument(
    "--exclude-accounts",
    nargs="+",
    help="Space-separated list of AWS account IDs to exclude from the inventory collection",
)

regions_group = arg_parser.add_argument_group(
    title=f"{GREEN}{BOLD}Regions selection{RESET}",
    description=f"({BOLD}default{RESET}: all regions)"
)

regions_group.add_argument(
    "--regions",
    nargs="+",
    help="Space-separated list of AWS regions to collect inventory from",
)

regions_group.add_argument(
    "--exclude-regions",
    nargs="+",
    help="Space-separated list of AWS regions to exclude from the inventory collection"
)

arg_parser.add_argument(
    "--debug",
    action="store_true",
    help="Enable verbose debug logging",
)

arg_parser.add_argument(
    "--version",
    action="version",
    version=f"Inventory Collector v{__version__}",
)

args = arg_parser.parse_args()

#############################
### Logginc configuration ###
#############################

class CustomFormatter(logging.Formatter):
    LEVELS = {
        logging.DEBUG: BLUE,
        logging.INFO: GREEN,
        logging.WARNING: YELLOW,
        logging.ERROR: RED,
        logging.CRITICAL: RED,
    }

    def __init__(self):
        super().__init__(
            f"{BLACK}%(asctime)s.%(msecs)03d UTC{RESET} {GREEN}%(levelname)s{RESET} "
            f"{BOLD}%(name)s{RESET}: %(message)s",
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    def format(self, record):
        level_color = CustomFormatter.LEVELS.get(record.levelno)

        if level_color is not None:
            record.levelname = f"{level_color}{record.levelname}{RESET}"

        return logging.Formatter.format(self, record)

logger = logging.getLogger()
logger.setLevel(logging.DEBUG if args.debug else logging.INFO)

handler = logging.StreamHandler(sys.stderr)

handler.setFormatter(CustomFormatter())
logger.addHandler(handler)

######################
### Business logic ###
######################

class App:
    _exit_stack: AsyncExitStack
    current_account: str

    # AWS clients
    _ec2: 'EC2Client'
    _efs: 'EFSClient'
    _fsx: 'FSxClient'
    _org: 'OrganizationsClient'
    _s3: 'S3Client'
    _sts: 'STSClient'

    def __init__(self):
        self._exit_stack = AsyncExitStack()

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self._exit_stack.__aexit__(exc_type, exc_value, traceback)

    async def __aenter__(self):
        session = aiobotocore.session.get_session()

        def create_client(name):
            return self._exit_stack.enter_async_context(session.create_client(name))

        timer = time.perf_counter()

        self._sts = await create_client('sts')
        self._org = await create_client('organizations')
        self._s3  = await create_client('s3')
        self._ec2 = await create_client('ec2')
        self._efs = await create_client('efs')
        self._fsx = await create_client('fsx')

        logger.info(f"Client creation took {time.perf_counter() - timer:.2f} seconds")

        identity = await self._sts.get_caller_identity()

        self.current_account = identity['Account']
        identity_arn = identity['Arn']

        logger.info(f"Current account:  {BOLD}{self.current_account}{RESET}")
        logger.info(f"Current identity: {BOLD}{identity_arn}{RESET}")

        return self

    async def run(self):
        accounts = await self.discover_accounts()
        if not accounts:
            raise Exception("No accounts were selected for processing. Nothing to do.")

        regions = await self.discover_regions()

        if not regions:
            raise Exception("No regions were selected for processing. Nothing to do.")

        logger.info("Starting inventory collection...")


    async def discover_regions(self) -> list[str]:
        if args.regions:
            regions: list[str] = args.regions
        else:
            response = await self._ec2.describe_regions()
            regions = [region['RegionName'] for region in response['Regions']]

        if args.exclude_regions:
            filtered_regions = [
                region for region in regions if region not in args.exclude_regions
            ]

            total_filtered = len(regions) - len(filtered_regions)

            regions = filtered_regions

            if total_filtered != 0:
                logger.info(
                    f"Excluded: {BOLD}{total_filtered}{RESET} regions "
                    f"({BOLD}{len(regions)}{RESET} will be processed)"
                )

        logger.info(f"Selected {GREEN}{BOLD}{len(regions)}{RESET} regions for processing")

        return regions

    async def discover_accounts(self) -> list[str]:
        details = []

        if args.all_accounts:
            accs = await self.list_all_accounts(details)
        elif args.accounts:
            accs: list[str] = args.accounts
        else:
            accs = [self.current_account]

        if args.exclude_accounts:
            filtered_accs = [
                acc for acc in accs if acc not in args.exclude_accounts
            ]

            total_filtered = len(accs) - len(filtered_accs)

            accs = filtered_accs

            if total_filtered != 0:
                details.append(f"excluded: {BOLD}{total_filtered}{RESET}")

        details = f" ({', '.join(details)}" if details else ""

        logger.info(
            f"Selected {GREEN}{BOLD}{len(accs)}{RESET} accounts for processing{details}"
        )

        return accs

    async def list_all_accounts(self, details: list[str]) -> list[str]:
        accs = [
            acc
            async for page in self._org.get_paginator('list_accounts').paginate()
            for acc in page['Accounts']
        ]

        total_accounts = len(accs)

        accs = [acc['Id'] for acc in accs if acc['Status'] == 'ACTIVE']

        active_accs = len(accs)
        inactive_accs = total_accounts - active_accs

        details.append(f"total: {BOLD}{total_accounts}{RESET}")
        details.append(f"active: {BOLD}{active_accs}{RESET}")
        details.append(f"inactive: {BOLD}{inactive_accs}{RESET}")

        return accs

async def main():
    try:
        async with App() as app:
            await app.run()
    except Exception as err:
        if args.debug:
            logger.exception(err)
        else:
            logger.error(err)
        return 1

    return 0


def on_cancel(sig_number: int, _frame):
    logger.error(
        f"Cancellation signal received: {signal.strsignal(sig_number)} ({sig_number}). "
        "Exiting..."
    )
    sys.exit(1)

# It's not possible to serialize dataclasses with the default JSON encoder.
# The reason Python restricts this is apparently to avoid confusion that
# deserializing into dataclasses doesn't work (JSON serialization is lossy):
# https://www.reddit.com/r/Python/comments/193lp4s/why_are_python_dataclasses_not_json_serializable/
#
# Some other primitive types in Python are also not JSON serializable, so we
# handle their serilization manually.
class AnyClassEncoder(json.JSONEncoder):
    def default(self, obj):
        if is_dataclass(obj):
            return asdict(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, set):
            return list(obj)
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return super().default(obj)

def to_json(value, indent = 2):
    return json.dumps(value, indent = indent, cls=AnyClassEncoder)

def print_json(label: str, value):
    print(to_json({ label: value }))

if __name__ == "__main__":
    signal.signal(signal.SIGINT, on_cancel)
    signal.signal(signal.SIGTERM, on_cancel)

    exit_code = asyncio.get_event_loop().run_until_complete(main())

    sys.exit(exit_code)
