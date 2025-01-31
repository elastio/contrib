#!/usr/bin/env python3

import argparse
import asyncio
import csv
import json
import logging
import signal
import sys
from contextlib import AsyncExitStack
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime
from typing import TYPE_CHECKING

__version__ = '0.33.0'

if TYPE_CHECKING:
    from types_aiobotocore_ec2 import EC2Client
    from types_aiobotocore_ec2.type_defs import TagTypeDef as Ec2Tag
    from types_aiobotocore_efs import EFSClient
    from types_aiobotocore_fsx import FSxClient
    from types_aiobotocore_organizations import OrganizationsClient
    from types_aiobotocore_s3 import S3Client
    from types_aiobotocore_sts import STSClient
    from aiobotocore.credentials import AioCredentials

GREEN = "\033[0;32m"
RED = "\033[0;31m"
YELLOW = "\033[0;33m"
BLACK = "\033[0;30m"
BLUE = "\033[0;34m"

RESET = "\033[0m"
BOLD = "\033[1m"

try:
    import aiobotocore.session
    import aiobotocore.config
    import aiobotocore.credentials
    from aiobotocore.session import AioSession
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
    _current_account: str
    _session: 'AioSession'
    _org: 'OrganizationsClient'
    _creds: 'AioCredentials'

    def __init__(self):
        self._exit_stack = AsyncExitStack()

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self._exit_stack.__aexit__(exc_type, exc_value, traceback)

    async def __aenter__(self):
        self._session = aiobotocore.session.get_session()
        self._creds = await self._session.get_credentials()

        if not self._creds:
            raise Exception("No credentials found. Please configure your AWS credentials.")

        self._org = self._exit_stack.enter_async_context(self._session.create_client("organizations"))
        sts = await self._exit_stack.enter_async_context(self._session.create_client("sts"))

        identity = await sts.get_caller_identity()

        self._current_account = identity['Account']
        identity_arn = identity['Arn']

        logger.info(f"Current account:  {BOLD}{self._current_account}{RESET}")
        logger.info(f"Current identity: {BOLD}{identity_arn}{RESET}")

        return self

    async def run(self):
        accs = await self.discover_accounts()
        if not accs:
            raise Exception("No accounts were selected for processing. Nothing to do.")

        regions = await self.discover_regions()

        if not regions:
            raise Exception("No regions were selected for processing. Nothing to do.")

        logger.info(f"{GREEN}Starting inventory collection...{RESET}")

        futs = [
            self.collect_inventory_in_region(acc, region)
            for acc in accs
            for region in regions
        ]

        assets = [
            asset
            for assets in await asyncio.gather(*futs)
            for asset in assets
        ]

        logger.info(
            f"{GREEN}Inventory collection completed. "
            f"{BOLD}{len(assets)}{RESET}{GREEN}assets collected.{RESET}"
        )

        if assets:
            with open('inventory.csv', mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([
                    'Account',
                    'Region',
                    'Type',
                    'Name',
                    'ID', 'State', 'Data Size (GiB)'
                ])
                for asset in assets:
                    writer.writerow([asset.account, asset.region, asset.type, asset.name, asset.id, asset.state, asset.data_size_gib])

        logger.info(f"{GREEN}Inventory collection completed. {len(assets)} assets collected.{RESET}")




    async def collect_inventory_in_region(self, account: str, region: str) -> list['Asset']:
        logger.info(f"Processing {BOLD}{account}/{region}{RESET}")

        session = await self.resolve_session(account, region)

        async with InventoryInRegion(session) as ctx:
            return await ctx.collect_inventory()

    async def resolve_session(self, account: str, region: str) -> 'SelfAwareAioSession':
        if account == self._current_account:
            return SelfAwareAioSession(account, region, self._session)

        # Looks like there is no official way in boto to bind the assume-role
        # credentials provider with the session other than accessing the private
        # _credentials field directly. This is very dumb, but it works.
        # https://stackoverflow.com/a/66346765/9259330
        session = AioSession(aws_access_key_id="", aws_secret_access_key="")

        sts_session = AioSession(aws_access_key_id="", aws_secret_access_key="")
        sts_session._credentials = self._creds

        assume_role_config = {
            "role_arn": f"arn:aws:iam::{account}:role/{args.assume_role}",
            "role_session_name": "inventory-collector",
        }

        profile_name="main"

        config = { profile_name: assume_role_config }

        provider = aiobotocore.credentials.AioAssumeRoleProvider(
            load_config=lambda: config,
            client_creator=sts_session.create_client,
            cache=dict,
            profile_name=profile_name,
        )

        session._credentials = await provider.load()

        return SelfAwareAioSession(account, region, session)


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
            accs = [self._current_account]

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

@dataclass
class SelfAwareAioSession:
    account: str
    region: str
    inner: AioSession

class InventoryInRegion:
    _ec2: 'EC2Client'
    _efs: 'EFSClient'
    _fsx: 'FSxClient'
    _s3: 'S3Client'

    def __init__(self, session: SelfAwareAioSession):
        self._exit_stack = AsyncExitStack()
        self._session = session

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self._exit_stack.__aexit__(exc_type, exc_value, traceback)

    async def __aenter__(self):
        enter_async = self._exit_stack.enter_async_context
        create_client = self._session.inner.create_client
        region = self._session.region

        self._ec2 = await enter_async(create_client("ec2", region_name=region))
        self._efs = await enter_async(create_client("efs", region_name=region))
        self._fsx = await enter_async(create_client("fsx", region_name=region))
        self._s3 = await enter_async(create_client("s3", region_name=region))

        return self

    async def collect_inventory(self) -> list['Asset']:
        return self.collect_inventory_ec2()

    async def collect_inventory_ec2(self) -> list['Asset']:
        def find_name_tag(tags: list['Ec2Tag']) -> str | None:
            return next((tag['Value'] for tag in tags if tag['Key'] == 'Name'), None)


        volumes = self._ec2.get_paginator('describe_volumes')
        volumes = volumes.paginate(
            Filters=[
                {
                    "Name": "status",
                    "Values": ["available", "in-use"]
                }
            ]
        )
        volumes = [
            Asset(
                account=self._session.account,
                region=self._session.region,
                type='ec2:volume',
                name=find_name_tag(volume.get('Tags', [])),
                state=volume.get('State'),
                data_size_gib=volume.get('Size')
            )
            async for page in volumes
            for volume in page['Volumes']
        ]

        instances = self._ec2.get_paginator('describe_instances')
        instances = instances.paginate(
            Filters=[
                {
                    "Name": "instance-state-name",
                    "Values": ["running", "stopping", "stopped"]
                }
            ]
        )
        instances = [
            Asset(
                account=self._session.account,
                region=self._session.region,
                type='ec2:instance',
                name=find_name_tag(instance.get('Tags', [])),
                state=instance.get('State', {}).get('Name'),
                data_size_gib=sum(
                    next(
                        (
                            volume.data_size_gib
                            for volume in volumes if volume.id == volume_id
                        ),
                        0
                    )
                    for mapping in instance.get('BlockDeviceMappings', [])
                    if (volume_id := mapping.get('Ebs', {}).get('VolumeId'))
                )
            )
            async for page in instances
            for instance in page['Reservations']
            for instance in instance['Instances']
        ]

        return instances + volumes


@dataclass
class Asset:
    account: str
    region: str
    type: str
    name: str
    id: str
    state: str
    # Size of the asset in GiB
    data_size_gib: int



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

    exit_code = asyncio.run(main())

    sys.exit(exit_code)
