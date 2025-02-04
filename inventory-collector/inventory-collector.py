#!/usr/bin/env python3

import argparse
import csv
import logging
import os
import platform
import signal
import sys
from dataclasses import dataclass, fields
from typing import TYPE_CHECKING, Iterable, Optional
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from datetime import datetime, timedelta

if TYPE_CHECKING:
    from mypy_boto3_s3.type_defs import BucketTypeDef

__version__ = "0.33.0"

GREEN = "\033[0;32m"
RED = "\033[0;31m"
YELLOW = "\033[0;33m"
PURPLE = "\033[0;35m"
BLUE = "\033[0;34m"

RESET = "\033[0m"
BOLD = "\033[1m"

try:
    import botocore.session
    import botocore.config
    import botocore.credentials
    from boto3 import Session
    from tqdm import tqdm
    from tqdm.contrib.logging import logging_redirect_tqdm
except ImportError as err:
    print(
        f"{RED}Import error: {err}{RESET}\n"
        "Install the dependencies with this command:\n"
        f"{GREEN}pip3 install --upgrade botocore boto3 tqdm{RESET}"
    )
    sys.exit(1)

default_session = Session()

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
    help="AWS region to use for the STS endpoint. "
    "Required for accessing opt-in regions (default: %(default)s)",
    default=default_session.region_name,
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
    default=max(20, os.cpu_count() or 1),
    help="Maximum number of concurrent API calls (default: %(default)s)",
)
arg_parser.add_argument(
    "--no-progress",
    action="store_true",
    help="Disable the progress bar",
)

arg_parser.add_argument(
    "--out-file",
    default="inventory.csv",
    help="Path to the file where to save the inventory data in CSV format (default: %(default)s)",
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
            f"{PURPLE}%(asctime)s.%(msecs)03d UTC{RESET} {GREEN}%(levelname)s{RESET} "
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
logging.getLogger("botocore.credentials").setLevel(logging.ERROR)


######################
### Business logic ###
######################


class App:
    def __init__(self):
        logger.info(
            f"Using botocore v{botocore.__version__}, Python v{platform.python_version()}"
        )

        self._creds = default_session.get_credentials()
        self._thread_pool = ThreadPoolExecutor(max_workers=args.concurrency)

        if not self._creds:
            raise Exception(
                "No credentials found. Please configure your AWS credentials."
            )

        self._org = default_session.client("organizations")
        sts = default_session.client("sts")

        identity = sts.get_caller_identity()

        self._current_account = identity["Account"]
        identity_arn = identity["Arn"]

        logger.info(f"Current account:  {BOLD}{self._current_account}{RESET}")
        logger.info(f"Current identity: {BOLD}{identity_arn}{RESET}")

    def run(self):
        accounts = self.list_accounts_rich()

        if not accounts:
            raise Exception("There are no accounts to process. Nothing to do.")

        account_regions = sum(len(account.regions) for account in accounts)

        if account_regions == 0:
            raise Exception("There are no regions to process. Nothing to do.")

        logger.info(
            f"{GREEN}Listing assets in {BOLD}{account_regions}{RESET} "
            f"{GREEN}account-regions (concurrency: {args.concurrency})...{RESET}"
        )

        progress = InventoryProgress(account_regions)

        batches = self._thread_pool.map(
            lambda account: self.list_assets_in_account(progress, account),
            accounts,
        )
        assets = sorted(
            (asset for assets in batches for asset in assets),
            key=lambda asset: (asset.type, asset.account_id, asset.region, asset.name),
        )

        logger.info(
            f"{GREEN}Inventory collection completed. "
            f"{BOLD}{len(assets)}{RESET} {GREEN}assets collected.{RESET}"
        )

        if not assets:
            logger.info("No assets were collected. Exiting...")
            return

        logger.info(f"Dumping the inventory data into {BOLD}{args.out_file}{RESET}...")

        with open(args.out_file, mode="w", newline="") as file:
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
                        asset.size_gib,
                    )
                )

    def assume_role_session(self, account: str) -> "Session":
        if account == self._current_account:
            return default_session

        # We provide means to override the STS endpoint to usee a regional one
        # because some newer AWS regions require using a regional endpoint,
        # otherwise credentials returned by AssumeRole would result in an error
        # something like "could not validate the provided access credentials".
        endpoint_url = f"https://sts.{args.sts_endpoint_region}.amazonaws.com"

        def client_creator(*args, **kwargs):
            return default_session.client(endpoint_url=endpoint_url, *args, **kwargs)

        fetcher = botocore.credentials.AssumeRoleCredentialFetcher(
            client_creator=client_creator,
            source_credentials=self._creds,
            role_arn=f"arn:aws:iam::{account}:role/{args.assume_role}",
            extra_args={
                "RoleSessionName": "inventory-collector",
            },
        )

        assume_role_creds = botocore.credentials.DeferredRefreshableCredentials(
            method="assume-role", refresh_using=fetcher.fetch_credentials
        )

        assume_role_session = botocore.session.Session()

        # Looks like there is no official way in boto to bind the assume-role
        # credentials provider with the session other than accessing the private
        # _credentials field directly. This is very dumb, but it works.
        # https://stackoverflow.com/a/66346765/9259330
        # Note on a potentially related memory leak that we work around:
        # https://github.com/boto/botocore/issues/3366
        assume_role_session._credentials = assume_role_creds

        return Session(botocore_session=assume_role_session)

    def enrich_account(self, account: "BasicAccount") -> Optional["RichAccount"]:
        session = self.assume_role_session(account.id)

        try:
            session.get_credentials().get_frozen_credentials()
        except Exception as err:
            logger.warning(
                f"[{account}] {YELLOW}{BOLD}Authentication to the account failed"
                f"{RESET}{YELLOW}: {err}{RESET}"
            )
            return None

        try:
            response = session.client("ec2").describe_regions()
        except Exception as err:
            logger.warning(
                f"[{account}] {YELLOW}{BOLD}ec2:DescribeRegions failed"
                f"{RESET}{YELLOW}: {err}{RESET}"
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

        return RichAccount(
            id=account.id,
            name=account.name,
            regions=sorted(regions),
        )

    def list_accounts_basic(self, details: list[str]) -> Optional[list["BasicAccount"]]:
        try:
            accounts = [
                account
                for page in self._org.get_paginator("list_accounts").paginate()
                for account in page["Accounts"]
            ]
        except Exception as err:
            # Rethrow the error, because we must have access to ListAccounts API
            # to be able to collect inventory data from all of them.
            if args.all_accounts:
                raise err

            logger.warning(
                f"{YELLOW}{BOLD}organizations:ListAccounts failed. There won't be account name "
                f"information in the inventory{RESET}{YELLOW}: {err}{RESET}"
            )
            return None

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

    def list_accounts_rich(self) -> list["RichAccount"]:
        details = []

        listed_accounts = self.list_accounts_basic(details)

        if args.all_accounts:
            accounts = listed_accounts
        else:
            accounts = args.accounts if args.accounts else [self._current_account]

            if listed_accounts is None:
                # We couldn't list accounts, so we can neither filter out non-existing
                # ones nor get their names. We will just use the IDs.
                accounts = [BasicAccount(id=account, name=None) for account in accounts]
            else:
                accounts = [
                    account
                    for account_id in accounts
                    if (
                        account := next(
                            (acc for acc in listed_accounts if acc.id == account_id),
                            None,
                        )
                    )
                ]

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
            f"{GREEN}Listing regions in {BOLD}{len(accounts)}{RESET} "
            f"{GREEN}selected accounts (concurrency: {args.concurrency})...{RESET}"
        )

        accounts_progress = progress_bar(
            total=len(accounts),
            unit="account",
            desc="(listing regions)",
        )

        def enrich_account(account):
            enriched = self.enrich_account(account)
            accounts_progress.update(1)
            return enriched

        rich_accs = self._thread_pool.map(enrich_account, accounts)
        rich_accs = [account for account in rich_accs if account]

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

    def list_assets_in_account(
        self,
        progress: "InventoryProgress",
        account: "RichAccount",
    ) -> Iterable["Asset"]:
        # We could store the `session` in the `RichAccount` object, but it would
        # would lead a memory leak in `botocore` preventing this script from being
        # able to run in Cloudshell: https://github.com/boto/botocore/issues/3366
        session = self.assume_role_session(account.id)

        assets = self._thread_pool.map(
            lambda region: self.list_assets_in_region(
                progress, session, account, region
            ),
            account.regions,
        )

        return (asset for assets in assets for asset in assets)

    def list_assets_in_region(
        self,
        progress: "InventoryProgress",
        session: "Session",
        account: "RichAccount",
        region: str,
    ) -> list["Asset"]:
        logger.debug(f"Processing {BOLD}{account}:{region}{RESET}")
        assets = ListAssetsInRegion(progress, session, account, region).run()
        progress.regions.update(1)
        return assets


class ListAssetsInRegion:
    def __init__(
        self,
        progress: "InventoryProgress",
        session: "Session",
        account: "RichAccount",
        region: str,
    ):
        self._account = account
        self._region = region
        self._progress = progress

        self._prefix = f"{YELLOW}[{account}:{region}]".ljust(29)

        self._cloudwatch = session.client("cloudwatch", region_name=region)
        self._ec2 = session.client("ec2", region_name=region)
        self._efs = session.client("efs", region_name=region)
        self._fsx = session.client("fsx", region_name=region)
        self._s3 = session.client("s3", region_name=region)

    def run(self) -> list["Asset"]:
        assets = {
            AssetType.EBS_VOLUME: self.list_ebs(),
            AssetType.EC2_INSTANCE: self.list_ec2(),
            AssetType.S3_BUCKET: self.list_s3(),
        }

        return [
            asset
            for asset_type, assets in assets.items()
            for asset in self.log_assets(assets, asset_type)
        ]

    def log_assets(self, assets: list["Asset"], type: "AssetType") -> list["Asset"]:
        logger.debug(
            f"{self._prefix} Discovered {BOLD}{len(assets)}{RESET} assets"
            f" of type {BOLD}{type}{RESET}"
        )
        return assets

    def log_api_error(self, api_name: str, err: Exception):
        logger.warning(f"{self._prefix} {api_name} failed: {err}{RESET}")

    def list_ebs(self) -> list["Asset"]:
        volumes = self._ec2.get_paginator("describe_volumes")
        volumes = volumes.paginate(
            Filters=[{"Name": "status", "Values": ["available", "in-use"]}]
        )

        try:
            return [
                self.asset(
                    type=AssetType.EBS_VOLUME,
                    id=volume["VolumeId"],
                    name=find_name_tag(volume.get("Tags", [])),
                    state=volume.get("State"),
                    size_gib=volume.get("Size"),

                    # There are no metrics about files count on an EBS volume
                    # in Cloudwatch, and we can't afford mounting the volumes
                    # to count the files, so we just skip this metric.
                    files=None,
                )
                for page in volumes
                for volume in page.get("Volumes", [])
            ]
        except Exception as err:
            self.log_api_error("ec2:DescribeVolumes", err)
            return []

    def list_ec2(self) -> list["Asset"]:
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
            return [
                self.asset(
                    type=AssetType.EC2_INSTANCE,
                    id=instance["InstanceId"],
                    name=find_name_tag(instance.get("Tags", [])),
                    state=instance.get("State", {}).get("Name"),

                    # We count the sizes of attached EBS volumes separately
                    size_gib=None,
                    files=None,
                )
                for page in instances
                for instance in page.get("Reservations", [])
                for instance in instance.get("Instances", [])
            ]
        except Exception as err:
            self.log_api_error("ec2:DescribeInstances", err)
            return []

    def list_s3(self) -> list["Asset"]:
        try:
            buckets = self._s3.list_buckets()
        except Exception as err:
            self.log_api_error("s3:ListBuckets", err)
            buckets = []

        return [
            self.enrich_s3_buckets(bucket)
            for bucket in buckets.get("Buckets", [])
        ]

    def enrich_s3_buckets(self, bucket: "BucketTypeDef") -> "Asset":
        # From the docs (https://docs.aws.amazon.com/AmazonS3/latest/userguide/cloudwatch-monitoring.html):
        # > These storage metrics for Amazon S3 are reported once per day.
        #
        # However, according to @Veetaha's experience looking at CloudWatch for these
        # metrics, there was a gap of ~1.5 day. We set the lag to 2.5 days to be safe.
        end_time=datetime.now()
        start_time = end_time - timedelta(days=2.5)

        bucket_name = bucket["Name"]

        bucket_size_bytes_id = "bucket_size_bytes"
        number_of_objects_id = "number_of_objects"

        try:
            response = self._cloudwatch.get_metric_data(
                StartTime=start_time,
                EndTime=end_time,
                ScanBy="TimestampDescending",
                MetricDataQueries=[
                    {
                        "Id": bucket_size_bytes_id,
                        "ReturnData": True,
                        "MetricStat": {
                            "Metric": {
                                "Namespace": "AWS/S3",
                                "MetricName": "BucketSizeBytes",
                                "Dimensions": [
                                    {"Name": "BucketName", "Value": bucket_name},
                                    {"Name": "StorageType", "Value": "StandardStorage"},
                                ],
                            },
                            "Stat": "Average",
                            "Period": 60 * 60 * 24,
                        },
                    },
                    {
                        "Id": number_of_objects_id,
                        "ReturnData": True,
                        "MetricStat": {
                            "Metric": {
                                "Namespace": "AWS/S3",
                                "MetricName": "NumberOfObjects",
                                "Dimensions": [
                                    {"Name": "BucketName", "Value": bucket_name},
                                    {"Name":"StorageType", "Value": "AllStorageTypes"},
                                ],
                            },
                            "Stat": "Average",
                            "Period": 60 * 60 * 24,
                        },
                    }
                ]
            )

            metrics = response["MetricDataResults"]
            messages = response["Messages"]
        except Exception as err:
            logger.warning(
                f"{self._prefix} cloudwatch:GetMetricStatistics failed: {err}{RESET}"
            )
            metrics = []
            messages = []

        for message in messages:
            logger.warning(
                f"{self._prefix} Got cloudwatch:GetMetricData message when getting "
                f"metrics for the S3 bucket '{bucket_name}': {message.get('Code')}: "
                f"{message.get('Value')}"
            )

        for metric in metrics:
            if messages := metric.get("Messages"):
                for message in messages:
                    logger.warning(
                        f"{self._prefix} Got cloudwatch:GetMetricData message for "
                        f"{metric.get("Id")} S3 metric (bucket: {bucket_name}: "
                        f"{message.get('Code')}: {message.get('Value')}"
                    )

            if (status := metric.get("StatusCode")) and status != "Complete" and status != "PartialData":
                logger.warning(
                    f"{self._prefix} Got cloudwatch:GetMetricData status {status} "
                    f"for {metric.get("Id")} S3 metric (bucket: {bucket_name})"
                )

        size_gib = next(
            (
                # Convert to GiB
                round(value / (2 ** 30), 2)
                for metric in metrics
                if metric.get("Id") == bucket_size_bytes_id
                for value in metric.get("Values", [])
            ),
            None,
        )

        files = next(
            (
                value
                for metric in metrics
                if metric.get("Id") == number_of_objects_id
                for value in metric.get("Values", [])
            ),
            None,
        )

        return self.asset(
            type=AssetType.S3_BUCKET,
            id=bucket_name,
            name=bucket_name,
            size_gib=size_gib,
            files=files,

            # Buckets don't have a state property
            state=None,
        )


    def asset(
        self,
        type: "AssetType",
        id: str,
        name: Optional[str],
        state: Optional[str],
        size_gib: Optional[int],
        files: Optional[int],
    ) -> "Asset":
        self._progress.add_asset(type, size_gib)

        return Asset(
            account_id=self._account.id,
            account_name=self._account.name,
            region=self._region,
            type=type,
            id=id,
            name=name,
            state=state,
            size_gib=size_gib,
            files=files,
        )


def find_name_tag(tags: list[dict]) -> Optional[str]:
    return next((tag["Value"] for tag in tags if tag["Key"] == "Name"), None)


class InventoryProgress:
    def __init__(self, total_regions: int):
        self.regions = progress_bar(
            total=total_regions,
            desc="(listing assets)",
            unit="account-region",
        )
        self._total_asset_metrics = AssetsMetrics(f"{BOLD}total assets{RESET}")
        self._per_asset_metrics: dict["AssetType", "AssetsMetrics"] = {
            type: AssetsMetrics(type.value) for type in AssetType
        }

    def add_asset(self, type: "AssetType", size_gib: Optional[int]):
        self._per_asset_metrics[type].incr(size_gib)
        self._total_asset_metrics.incr(size_gib)


class AssetType(str, Enum):
    EBS_VOLUME = "ebs:volume"
    EC2_INSTANCE = "ec2:instance"
    S3_BUCKET = "s3:bucket"


class AssetsMetrics:
    def __init__(self, label: str):
        self._label = label
        self._data_in_gib = 0
        self._count = tqdm(
            bar_format=f"{GREEN}{BOLD}{{n_fmt}}{RESET} {{desc}}{RESET}",
            desc=self.description(),
        )

    def description(self):
        data_size = (
            f" ({GREEN}{BOLD}{self._data_in_gib}{RESET} GiB)"
            if self._data_in_gib
            else ""
        )

        return f"{self._label}{data_size}"

    def incr(self, size_gib: Optional[int]):
        self._count.update(1)
        self._data_in_gib = round(self._data_in_gib + (size_gib or 0), 2)

        self._count.set_description_str(self.description())


def progress_bar(unit: str, total: int, desc: str) -> tqdm:
    return tqdm(
        total=total,
        unit=unit,
        disable=args.no_progress,
        leave=True,
        desc=desc,
        bar_format=(
            f"{GREEN}{BOLD}{{n_fmt}} / {{total_fmt}} {{unit}}s{RESET} "
            f"{BLUE}[elapsed: {{elapsed}}, ETA: {{remaining}}]{RESET} "
            f"{PURPLE}[{{rate_fmt}}]{RESET} "
            f"{GREEN}{BOLD}{{desc}}: {{percentage:3.0f}}%{RESET} {{bar}}"
        ),
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
    regions: list[str]

    def __str__(self):
        return f"{self.id} ({self.name})"


@dataclass
class Asset:
    type: str
    account_id: str
    account_name: Optional[str]
    region: str
    name: Optional[str]
    id: str
    state: Optional[str]

    # Size of the asset in GiB
    size_gib: Optional[int]

    # Total number of files if available
    files: Optional[int]


def main():
    try:
        with logging_redirect_tqdm([logger]):
            App().run()
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

    sys.exit(main())
