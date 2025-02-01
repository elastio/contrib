#!/usr/bin/env python3

import argparse
import asyncio
import csv
import logging
import signal
import sys
from contextlib import AsyncExitStack
from dataclasses import dataclass, fields
from typing import TYPE_CHECKING, Optional

__version__ = "0.33.0"

if TYPE_CHECKING:
    from types_aiobotocore_ec2 import EC2Client
    from types_aiobotocore_ec2.type_defs import TagTypeDef as Ec2Tag
    from types_aiobotocore_efs import EFSClient
    from types_aiobotocore_fsx import FSxClient
    from types_aiobotocore_organizations import OrganizationsClient
    from types_aiobotocore_s3 import S3Client
    from aiobotocore.credentials import AioCredentials

GREEN = "\033[0;32m"
RED = "\033[0;31m"
YELLOW = "\033[0;33m"
GREY = "\033[0;37m"
BLUE = "\033[0;34m"

RESET = "\033[0m"
BOLD = "\033[1m"

try:
    import aiobotocore.session
    import aiobotocore.config
    import aiobotocore.credentials
    from aiobotocore.session import AioSession
    from tqdm import tqdm
    from tqdm.contrib.logging import logging_redirect_tqdm
except ImportError as err:
    print(
        f"{RED}Import error: {err}{RESET}\n"
        "Install the dependencies with this command:\n"
        f"{GREEN}pip3 install --upgrade aiobotocore tqdm{RESET}"
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
    help="Name of the IAM role to assume in the processed accounts (default: %(default)s)",
    default="OrganizationAccountAccessRole",
)
auth_group.add_argument(
    "--sts-endpoint-region",
    help="AWS region to use for the STS endpoint (default: %(default)s). "
    "Required for accessing opt-in regions.",
    default=aiobotocore.session.get_session().get_config_variable("region"),
)

accs_group = arg_parser.add_argument_group(
    title=f"{GREEN}{BOLD}Accounts selection{RESET}",
    description=f"({BOLD}default{RESET}: current account only)",
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
    description=f"({BOLD}default{RESET}: all regions)",
)

regions_group.add_argument(
    "--regions",
    nargs="+",
    help="Space-separated list of AWS regions to collect inventory from",
)

regions_group.add_argument(
    "--exclude-regions",
    nargs="+",
    help="Space-separated list of AWS regions to exclude from the inventory collection",
)

arg_parser.add_argument(
    "--concurrency",
    type=int,
    default=40,
    help="Maximum number of concurrent API calls (default: %(default)s)",
)
arg_parser.add_argument(
    "--no-progress",
    action="store_true",
    help="Disable the progress bar",
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
### Logging configuration ###
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
            f"{GREY}%(asctime)s.%(msecs)03d UTC{RESET} {GREEN}%(levelname)s{RESET} "
            f"{BOLD}%(name)s{RESET}: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
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

# There are some noisy logs from this module. We provide better logging instead
logging.getLogger("aiobotocore.credentials").setLevel(logging.ERROR)


######################
### Business logic ###
######################


class App:
    _current_account: str
    _session: "AioSession"
    _org: "OrganizationsClient"
    _creds: "AioCredentials"

    def __init__(self):
        self._exit_stack = AsyncExitStack()
        self._semaphore = asyncio.Semaphore(args.concurrency)

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self._exit_stack.__aexit__(exc_type, exc_value, traceback)

    async def __aenter__(self):
        self._session = aiobotocore.session.get_session()
        self._creds = await self._session.get_credentials()

        if not self._creds:
            raise Exception(
                "No credentials found. Please configure your AWS credentials."
            )

        self._org = await self._exit_stack.enter_async_context(
            self._session.create_client("organizations")
        )
        sts = await self._exit_stack.enter_async_context(
            self._session.create_client("sts")
        )

        identity = await sts.get_caller_identity()

        self._current_account = identity["Account"]
        identity_arn = identity["Arn"]

        logger.info(f"Current account:  {BOLD}{self._current_account}{RESET}")
        logger.info(f"Current identity: {BOLD}{identity_arn}{RESET}")

        return self

    async def run(self):
        accounts = await self.list_accounts_rich()
        if not accounts:
            raise Exception("No accounts were selected for processing. Nothing to do.")

        regions = sum(len(account.regions) for account in accounts)

        if regions == 0:
            raise Exception("No regions were selected for processing. Nothing to do.")

        logger.info(f"{GREEN}Starting inventory collection...{RESET}")

        progress = InventoryProgress(regions)

        futs = [
            self.collect_inventory_in_account(progress, account) for account in accounts
        ]

        with logging_redirect_tqdm([logger]):
            assets = [
                asset for assets in await asyncio.gather(*futs) for asset in assets
            ]

        logger.info(
            f"{GREEN}Inventory collection completed. "
            f"{BOLD}{len(assets)}{RESET} {GREEN}assets collected.{RESET}"
        )

        if not assets:
            logger.info("No assets were collected. Exiting...")
            return

        with open("inventory.csv", mode="w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(field.name for field in fields(Asset))
            for asset in assets:
                writer.writerow(
                    (
                        asset.account_id,
                        asset.account_name,
                        asset.region,
                        asset.type,
                        asset.name,
                        asset.id,
                        asset.state,
                        asset.data_size_gib,
                    )
                )

    async def collect_inventory_in_account(
        self,
        progress: "InventoryProgress",
        account: "RichAccount",
    ) -> list["Asset"]:
        futs = (
            self.collect_inventory_in_region(progress, account, region)
            for region in account.regions
        )

        return [asset for assets in await asyncio.gather(*futs) for asset in assets]

    async def collect_inventory_in_region(
        self,
        progress: "InventoryProgress",
        account: "RichAccount",
        region: str,
    ) -> list["Asset"]:
        async with self._semaphore:
            logger.debug(f"Processing {BOLD}{account}:{region}{RESET}")

            async with InventoryInRegion(progress, account, region) as ctx:
                inventory = await ctx.collect_inventory()
                progress.regions.update(1)
                return inventory

    def assume_role_session(self, account: str) -> "AioSession":
        if account == self._current_account:
            return self._session

        # Looks like there is no official way in boto to bind the assume-role
        # credentials provider with the session other than accessing the private
        # _credentials field directly. This is very dumb, but it works.
        # https://stackoverflow.com/a/66346765/9259330
        endpoint_url = f"https://sts.{args.sts_endpoint_region}.amazonaws.com"

        def client_creator(*args, **kwargs):
            return self._session.create_client(
                endpoint_url=endpoint_url, *args, **kwargs
            )

        fetcher = aiobotocore.credentials.AioAssumeRoleCredentialFetcher(
            client_creator=client_creator,
            source_credentials=self._creds,
            role_arn=f"arn:aws:iam::{account}:role/{args.assume_role}",
            extra_args={
                "RoleSessionName": "inventory-collector",
            },
        )

        assume_role_creds = aiobotocore.credentials.AioDeferredRefreshableCredentials(
            method="assume-role", refresh_using=fetcher.fetch_credentials
        )

        assume_role_session = AioSession()
        assume_role_session._credentials = assume_role_creds

        return assume_role_session

    async def enrich_account(
        self, accounts_progress: tqdm, account: "BasicAccount"
    ) -> Optional["RichAccount"]:
        async with self._semaphore:
            return await self.enrich_account_(accounts_progress, account)

    async def enrich_account_(
        self, accounts_progress: tqdm, account: "BasicAccount"
    ) -> Optional["RichAccount"]:
        session = self.assume_role_session(account.id)

        try:
            await (await session.get_credentials()).get_frozen_credentials()
        except Exception as err:
            logger.warning(
                f"[{account}] {BOLD}Authentication to the account failed{RESET}: {err}"
            )
            return None

        try:
            async with session.create_client("ec2") as ec2:
                response = await ec2.describe_regions()
        except Exception as err:
            logger.warning(
                f"[{account}] {BOLD}ec2:DescribeRegions failed{RESET}: {err}"
            )
            return None

        all_regions = [region["RegionName"] for region in response["Regions"]]

        if args.regions:
            regions = [region for region in args.regions if region in all_regions]
        else:
            regions = all_regions

        if args.exclude_regions:
            regions = [
                region for region in regions if region not in args.exclude_regions
            ]

        accounts_progress.update(1)

        return RichAccount(
            id=account.id,
            name=account.name,
            session=session,
            regions=sorted(regions),
        )

    async def list_accounts_rich(self) -> list["RichAccount"]:
        details = []

        all_accounts = await self.list_accounts_basic(details)

        if args.all_accounts:
            accounts = all_accounts
        elif args.accounts:
            accounts = [
                account for account in all_accounts if account.id in args.accounts
            ]
        else:
            account = next(
                (
                    account
                    for account in all_accounts
                    if account.id == self._current_account
                ),
                None,
            )
            accounts = [account] if account else []

        if args.exclude_accounts:
            filtered_accs = [
                account
                for account in accounts
                if account.id not in args.exclude_accounts
            ]

            excluded = len(accounts) - len(filtered_accs)

            accounts = filtered_accs

            if excluded != 0:
                details.append(f"excluded: {BOLD}{excluded}{RESET}")

        logger.info(
            f"Discovering regions in {BOLD}{len(accounts)}{RESET} selected accounts..."
        )

        accounts_progress = progress_bar(
            total=len(accounts),
            unit="account",
        )

        futs = (self.enrich_account(accounts_progress, account) for account in accounts)

        with logging_redirect_tqdm([logger]):
            rich_accs = [account for account in await asyncio.gather(*futs) if account]

        accounts_progress.clear()

        if len(rich_accs) < len(accounts):
            details.append(
                f"inaccessible: {YELLOW}{BOLD}{len(accounts) - len(rich_accs)}{RESET}"
            )

        details = f" ({', '.join(details)})" if details else ""

        logger.info(
            f"Selected {GREEN}{BOLD}{len(accounts)}{RESET} accounts for processing{details}"
        )

        return rich_accs

    async def list_accounts_basic(self, details: list[str]) -> list["BasicAccount"]:
        accounts = [
            account
            async for page in self._org.get_paginator("list_accounts").paginate()
            for account in page["Accounts"]
        ]

        total_accounts = len(accounts)

        accounts = [
            BasicAccount(id=account["Id"], name=account.get("Name"))
            for account in accounts
            if account["Status"] == "ACTIVE"
        ]

        active_accs = len(accounts)
        inactive_accs = total_accounts - active_accs

        details.append(f"total: {BOLD}{total_accounts}{RESET}")
        details.append(f"active: {BOLD}{active_accs}{RESET}")
        details.append(f"inactive: {BOLD}{inactive_accs}{RESET}")

        return accounts


class InventoryInRegion:
    _ec2: "EC2Client"
    _efs: "EFSClient"
    _fsx: "FSxClient"
    _s3: "S3Client"

    def __init__(
        self, progress: "InventoryProgress", account: "RichAccount", region: str
    ):
        self._exit_stack = AsyncExitStack()
        self._account = account
        self._region = region
        self._progress = progress

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self._exit_stack.__aexit__(exc_type, exc_value, traceback)

    async def __aenter__(self):
        enter_async = self._exit_stack.enter_async_context
        create_client = self._account.session.create_client
        region = self._region

        self._ec2 = await enter_async(create_client("ec2", region_name=region))
        self._efs = await enter_async(create_client("efs", region_name=region))
        self._fsx = await enter_async(create_client("fsx", region_name=region))
        self._s3 = await enter_async(create_client("s3", region_name=region))

        return self

    async def collect_inventory(self) -> list["Asset"]:
        return await self.collect_inventory_ec2()

    async def collect_inventory_ec2(self) -> list["Asset"]:
        def find_name_tag(tags: list["Ec2Tag"]) -> str | None:
            return next((tag["Value"] for tag in tags if tag["Key"] == "Name"), None)

        volumes = self._ec2.get_paginator("describe_volumes")
        volumes = volumes.paginate(
            Filters=[{"Name": "status", "Values": ["available", "in-use"]}]
        )

        prefix = f"[{self._account}:{self._region}]".ljust(29)

        try:
            volumes = [
                self.asset(
                    type="ec2:volume",
                    id=volume["VolumeId"],
                    name=find_name_tag(volume.get("Tags", [])),
                    state=volume.get("State"),
                    data_size_gib=volume.get("Size"),
                )
                async for page in volumes
                for volume in page["Volumes"]
            ]
        except Exception as err:
            logger.warning(f"{prefix} ec2:DescribeVolumes failed: {err}")
            volumes = []

        logger.debug(
            f"{prefix} Discovered {BOLD}{len(volumes)}{RESET} assets of type {BOLD}ec2:volume{RESET}"
        )

        instances = self._ec2.get_paginator("describe_instances")
        instances = instances.paginate(
            Filters=[
                {
                    "Name": "instance-state-name",
                    "Values": ["running", "stopping", "stopped"],
                }
            ]
        )

        try:
            instances = [
                self.asset(
                    type="ec2:instance",
                    id=instance["InstanceId"],
                    name=find_name_tag(instance.get("Tags", [])),
                    state=instance.get("State", {}).get("Name"),
                    data_size_gib=sum(
                        next(
                            (
                                volume.data_size_gib
                                for volume in volumes
                                if volume.id == volume_id
                            ),
                            0,
                        )
                        for mapping in instance.get("BlockDeviceMappings", [])
                        if (volume_id := mapping.get("Ebs", {}).get("VolumeId"))
                    ),
                )
                async for page in instances
                for instance in page["Reservations"]
                for instance in instance["Instances"]
            ]
        except Exception as err:
            logger.warning(f"{prefix} ec2:DescribeInstances failed: {err}")
            instances = []

        logger.debug(
            f"{prefix} Discovered {BOLD}{len(instances)}{RESET} assets of type {BOLD}ec2:instance{RESET}"
        )

        return instances + volumes

    def asset(
        self,
        type: str,
        id: str,
        name: Optional[str],
        state: Optional[str],
        data_size_gib: Optional[int],
    ) -> "Asset":
        self._progress.assets.update(1)
        if data_size_gib:
            self._progress.data.update(data_size_gib)

        return Asset(
            account_id=self._account.id,
            account_name=self._account.name,
            region=self._region,
            type=type,
            id=id,
            name=name,
            state=state,
            data_size_gib=0,
        )


class InventoryProgress:
    regions: "tqdm"
    assets: "tqdm"
    data: "tqdm"

    def __init__(self, total_regions: int):
        self.regions = progress_bar(
            total=total_regions,
            unit="region",
            leave=True,
        )
        self.assets = tqdm(
            disable=args.no_progress,
            bar_format=f"{GREEN}{BOLD}{{n_fmt}} assets{RESET}",
        )
        self.data = tqdm(
            disable=args.no_progress,
            bar_format=f"{GREEN}{BOLD}{{n_fmt}} GiB{RESET}",
        )


def progress_bar(unit: str, total: int, leave=False) -> tqdm:
    return tqdm(
        total=total,
        unit=unit,
        disable=args.no_progress,
        leave=leave,
        bar_format=(
            f"{GREEN}{BOLD}{{n_fmt}} / {{total_fmt}} {{unit}}s{RESET} "
            f"{BLUE}[Elapsed: {{elapsed}} ETA: {{remaining}}]{RESET} "
            f"{GREY}[{{rate_fmt}}]{RESET} "
            f"{GREEN}{BOLD}{{percentage:3.0f}}%{RESET} {{bar}}"
        )
    )


@dataclass
class BasicAccount:
    id: str
    name: Optional[str]

    def __str__(self):
        return f"{self.id} ({self.name})"


@dataclass
class RichAccount:
    id: str
    name: Optional[str]
    session: "AioSession"
    regions: list[str]

    def __str__(self):
        return f"{self.id} ({self.name})"


@dataclass
class Asset:
    account_id: str
    account_name: Optional[str]
    region: str
    type: str
    name: Optional[str]
    id: str
    state: Optional[str]
    # Size of the asset in GiB
    data_size_gib: Optional[int]


async def main():
    try:
        async with App() as app:
            await app.run()
    except Exception as err:
        logger.exception(err)
        return 1

    return 0


def on_cancel(sig_number: int, _frame):
    logger.error(
        f"Cancellation signal received: {signal.strsignal(sig_number)} ({sig_number}). "
        "Exiting..."
    )
    sys.exit(1)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, on_cancel)
    signal.signal(signal.SIGTERM, on_cancel)

    exit_code = asyncio.run(main())

    sys.exit(exit_code)
