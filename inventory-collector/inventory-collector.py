#!/usr/bin/env python3

import argparse
import csv
import itertools
import logging
import os
import platform
import signal
import sys
from dataclasses import dataclass, fields
from typing import TYPE_CHECKING, Iterable, Iterator, Optional, TypeVar
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from datetime import datetime, timedelta

if TYPE_CHECKING:
    from mypy_boto3_cloudwatch.type_defs import MetricDataQueryTypeDef

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
    import botocore.exceptions
    from boto3 import Session
    from tqdm import tqdm
    from tqdm.contrib.logging import logging_redirect_tqdm
except ImportError as err:
    print(
        f"{RED}Import error: {err}{RESET}\n"
        "Install the dependencies with this command:\n"
        f"{GREEN}pip3 install --upgrade boto3 botocore tqdm{RESET}"
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
    default=max(40, os.cpu_count() or 1),
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


def api_error_logger(prefix: str):
    def impl(api_name: str, err: Exception):
        logger.warning(
            f"{prefix} {YELLOW}{BOLD}{api_name} failed{RESET}: {YELLOW}{err}{RESET}"
        )

    return impl


######################
### Business logic ###
######################


class App:
    def __init__(self):
        logger.info(
            f"Using botocore v{botocore.__version__}, Python v{platform.python_version()}"
        )

        self._creds = default_session.get_credentials()

        # These two pools try to balance between the concurrency of iterating
        # over accounts and over sub-account resources. Ideally, we should have
        # just one thread pool for everything, but this way it's much simpler
        # to code. It also avoids the problem of pre-constructing the list of
        # all `Session` objects in memory (which leads to gigabytes of RAM
        # memory usage due to https://github.com/boto/botocore/issues/3366)
        self._accounts_thread_pool = ThreadPoolExecutor(
            max_workers=int(args.concurrency * 0.3)
        )
        self._sub_accounts_thread_pool = ThreadPoolExecutor(
            max_workers=int(args.concurrency * 0.7)
        )

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
            f"{GREEN}account-regions...{RESET}"
        )

        progress = InventoryProgress(account_regions)

        batches = self._accounts_thread_pool.map(
            lambda account: self.list_assets_in_regions(progress, account),
            accounts,
        )
        assets = sorted(
            (asset for assets in batches for asset in assets),
            key=lambda asset: (
                asset.type,
                asset.account_id,
                asset.region or "",
                asset.name or "",
            ),
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
                        asset.type,
                        asset.account_id,
                        asset.account_name,
                        asset.region,
                        asset.name,
                        asset.id,
                        asset.state,
                        asset.size,
                        asset.files,
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

        log_api_err = api_error_logger(f"{BLUE}[{account.id}]{RESET}")

        try:
            session.get_credentials().get_frozen_credentials()
        except Exception as err:
            log_api_err("Authentication to the account", err)
            return None

        try:
            response = session.client("ec2").describe_regions()
        except Exception as err:
            log_api_err("ec2:DescribeRegions", err)
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

        # List S3 buckets separately. ListBuckets returns buckets from all regions,
        # so we list them only in the default region and then distribute enrichment
        # to regional asset listing.
        s3 = session.client("s3")
        try:
            s3_buckets = [
                bucket["Name"] for bucket in s3.list_buckets().get("Buckets", [])
            ]
        except Exception as err:
            log_api_err("s3:ListBuckets", err)
            s3_buckets = []

        regions = {region: RichRegion(name=region, s3_buckets=[]) for region in regions}

        def get_bucket_region(bucket: str):
            try:
                response = s3.head_bucket(Bucket=bucket)
            except botocore.exceptions.ClientError as err:
                # We can get the region from the response headers even if
                # we don't have access to calling HeadBucket
                response = err.response
            except Exception as err:
                log_api_err("s3:HeadBucket", err)
                return

            region = (
                response.get("ResponseMetadata", {})
                .get("HTTPHeaders", {})
                .get("x-amz-bucket-region", "")
            )

            if region is None:
                logger.warning(
                    f"{self._prefix} {YELLOW}Couldn't get region "
                    f"for bucket {bucket}. Ignoring it{RESET}"
                )
                return

            if region := regions.get(region):
                region.s3_buckets.append(bucket)

        self._sub_accounts_thread_pool.map(
            get_bucket_region,
            s3_buckets,
        )

        return RichAccount(
            id=account.id,
            name=account.name,
            regions=regions,
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
            if account.get("Status") == "ACTIVE"
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
            f"{GREEN}Listing global resources in {BOLD}{len(accounts)}{RESET} "
            f"{GREEN}selected accounts...{RESET}"
        )

        accounts_progress = progress_bar(
            total=len(accounts),
            unit="account",
            desc="(listing global resources)",
        )

        def enrich_account(account):
            enriched = self.enrich_account(account)
            accounts_progress.update(1)
            return enriched

        rich_accs = self._accounts_thread_pool.map(enrich_account, accounts)
        rich_accs = [account for account in rich_accs if account]

        if len(rich_accs) < len(accounts):
            details.append(
                f"inaccessible: {YELLOW}{BOLD}{len(accounts) - len(rich_accs)}{RESET}"
            )

        details = f" ({', '.join(details)})" if details else ""

        logger.info(
            f"Selected {GREEN}{BOLD}{len(accounts)}{RESET} accounts for processing{details}"
        )

        return rich_accs

    def list_assets_in_regions(
        self,
        progress: "InventoryProgress",
        account: "RichAccount",
    ) -> Iterable["Asset"]:
        # We could store the `session` in the `RichAccount` object, but it would
        # would lead a memory leak in `botocore` preventing this script from being
        # able to run in Cloudshell: https://github.com/boto/botocore/issues/3366
        session = self.assume_role_session(account.id)
        assets = self._sub_accounts_thread_pool.map(
            lambda region: self.list_assets_in_region(
                progress, account, session, region
            ),
            account.regions.values(),
        )

        return (asset for assets in assets for asset in assets)

    def list_assets_in_region(
        self,
        progress: "InventoryProgress",
        account: "RichAccount",
        session: "Session",
        region: "RichRegion",
    ) -> list["Asset"]:
        logger.debug(f"Processing {BOLD}{account}:{region.name}{RESET}")

        list_in_region = ListAssetsInRegion(progress, session, account, region)

        assets = list_in_region.run()

        progress.regions.update(1)

        return assets


class AssetType(str, Enum):
    EBS_VOLUME = "ebs:volume"
    EC2_INSTANCE = "ec2:instance"
    S3_BUCKET = "s3:bucket"
    EFS_FILE_SYSTEM = "efs:file-system"
    FSX_ONTAP_VOLUME = "fsx:ontap-volume"


@dataclass
class Asset:
    type: str
    account_id: str
    account_name: Optional[str]
    region: str
    name: Optional[str]
    id: str
    state: Optional[str]

    # Size of the asset in bytes if available
    size: Optional[int]

    # Total number of files if available
    files: Optional[int]


class ListAssetsInRegion:
    def __init__(
        self,
        progress: "InventoryProgress",
        session: "Session",
        account: "RichAccount",
        region: "RichRegion",
    ):
        self._account = account
        self._region = region
        self._progress = progress

        self._prefix = f"{BLUE}[{account}:{region.name}]{RESET}".ljust(29)
        self._log_api_error = api_error_logger(self._prefix)

        self._cloudwatch = session.client("cloudwatch", region_name=region.name)
        self._ec2 = session.client("ec2", region_name=region.name)
        self._efs = session.client("efs", region_name=region.name)
        self._fsx = session.client("fsx", region_name=region.name)
        self._s3 = session.client("s3", region_name=region.name)
        self._efs = session.client("efs", region_name=region.name)

    def run(self) -> list["Asset"]:
        assets = (
            self.list_ebs(),
            self.list_ec2(),
            self.enrich_s3_buckets(),
            self.list_efs(),
            self.list_fsx_ontap_volumes(),
        )

        return [
            asset
            for assets in assets
            for asset in assets
        ]

    def asset(
        self,
        type: "AssetType",
        id: str,
        name: Optional[str],
        state: Optional[str],
        size: Optional[int],
        files: Optional[int],
    ) -> "Asset":
        self._progress.add_asset(type, size)

        return Asset(
            account_id=self._account.id,
            account_name=self._account.name,
            region=self._region.name,
            type=type,
            id=id,
            name=name,
            state=state,
            size=size,
            files=files,
        )

    def log_api_error(self, api_name: str, err: Exception):
        logger.warning(f"{self._prefix} {YELLOW}{api_name} failed: {err}{RESET}")

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
                    name=find_name_tag(volume.get("Tags")),
                    state=volume.get("State"),
                    # Convert GiB to bytes
                    size=size * (2**30) if (size := volume.get("Size")) else None,
                    # There are no metrics about files count on an EBS volume
                    # in Cloudwatch, and we can't afford mounting the volumes
                    # to count the files, so we just skip this metric.
                    files=None,
                )
                for page in volumes
                for volume in page.get("Volumes", [])
            ]
        except Exception as err:
            self._log_api_error("ec2:DescribeVolumes", err)
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
                    name=find_name_tag(instance.get("Tags")),
                    state=instance.get("State", {}).get("Name"),
                    # We count the sizes of attached EBS volumes separately
                    size=None,
                    files=None,
                )
                for page in instances
                for instance in page.get("Reservations", [])
                for instance in instance.get("Instances", [])
            ]
        except Exception as err:
            self._log_api_error("ec2:DescribeInstances", err)
            return []

    def enrich_s3_buckets(self) -> list["Asset"]:
        if not self._region.s3_buckets:
            return []

        # From the docs (https://docs.aws.amazon.com/AmazonS3/latest/userguide/cloudwatch-monitoring.html):
        # > These storage metrics for Amazon S3 are reported once per day.
        #
        # However, according to @Veetaha's experience looking at CloudWatch for these
        # metrics, there was a gap of ~1.5 day. We set the lag to 2.5 days to be safe.
        end_time = datetime.now()
        start_time = end_time - timedelta(days=2.5)

        queries = (
            query
            for i, bucket in enumerate(self._region.s3_buckets)
            for query in (
                {
                    "Id": f"bucket_size_bytes_{i}",
                    "Label": f"{bucket} bucket size",
                    "ReturnData": True,
                    "MetricStat": {
                        "Metric": {
                            "Namespace": "AWS/S3",
                            "MetricName": "BucketSizeBytes",
                            "Dimensions": [
                                {"Name": "BucketName", "Value": bucket},
                                {"Name": "StorageType", "Value": "StandardStorage"},
                            ],
                        },
                        "Stat": "Average",
                        "Period": 60 * 60 * 24,
                    },
                },
                {
                    "Id": f"number_of_objects_{i}",
                    "Label": f"{bucket} number of objects",
                    "ReturnData": True,
                    "MetricStat": {
                        "Metric": {
                            "Namespace": "AWS/S3",
                            "MetricName": "NumberOfObjects",
                            "Dimensions": [
                                {"Name": "BucketName", "Value": bucket},
                                {"Name": "StorageType", "Value": "AllStorageTypes"},
                            ],
                        },
                        "Stat": "Average",
                        "Period": 60 * 60 * 24,
                    },
                },
            )
        )

        query_chunks = chunks(queries, 500)

        results: list[list[MetricDataQueryTypeDef]] = []

        for queries in query_chunks:
            try:
                response = self._cloudwatch.get_metric_data(
                    StartTime=start_time,
                    EndTime=end_time,
                    ScanBy="TimestampDescending",
                    MetricDataQueries=queries,
                )

                metrics = response["MetricDataResults"]
                messages = response["Messages"]
            except Exception as err:
                self._log_api_error(
                    f"{self._prefix} cloudwatch:GetMetricData failed: {err}{RESET}"
                )
                metrics = []
                messages = []

            for message in messages:
                logger.warning(
                    f"{self._prefix} Got cloudwatch:GetMetricData message when getting "
                    f"metrics for S3: {message.get('Code')}: {message.get('Value')}"
                )

            for metric in metrics:
                if messages := metric.get("Messages"):
                    for message in messages:
                        logger.warning(
                            f"{self._prefix} Got cloudwatch:GetMetricData message for "
                            f"{metric.get('Id')} S3 metric: {message.get('Code')}: {message.get('Value')}"
                        )

                if (status := metric.get("StatusCode")) and status not in (
                    "Complete",
                    "PartialData",
                ):
                    logger.warning(
                        f"{self._prefix} Got cloudwatch:GetMetricData status {status} "
                        f"for {metric.get('Id')} S3 metric"
                    )

                results.append(metrics)

        assets = [
            self.asset(
                type=AssetType.S3_BUCKET,
                id=bucket,
                name=bucket,
                size=next(
                    (
                        int(value)
                        for metrics in results
                        for metric in metrics
                        if metric.get("Id") == f"bucket_size_bytes_{i}"
                        for value in metric.get("Values", [])
                    ),
                    None,
                ),
                files=next(
                    (
                        int(value)
                        for metrics in results
                        for metric in metrics
                        if metric.get("Id") == f"number_of_objects_{i}"
                        for value in metric.get("Values", [])
                    ),
                    None,
                ),
                # Buckets don't have a state property
                state=None,
            )
            for i, bucket in enumerate(self._region.s3_buckets)
        ]

        return assets

    def list_efs(self) -> list["Asset"]:
        file_systems = self._efs.get_paginator("describe_file_systems")

        try:
            return [
                self.asset(
                    type=AssetType.EFS_FILE_SYSTEM,
                    id=fs["FileSystemId"],
                    name=find_name_tag(fs.get("Tags")),
                    state=state,
                    size=fs.get("SizeInBytes", {}).get("Value"),

                    # There are no metrics about files count on an EFS filesystem
                    # in Cloudwatch, and we can't afford mounting the volumes
                    # to count the files, so we just skip this metric.
                    files=None,
                )
                for page in file_systems.paginate()
                for fs in page["FileSystems"]
                if (state := fs.get("LifeCycleState"))
                not in ("deleted", "deleting", "error")
            ]
        except Exception as err:
            self._log_api_error("efs:DescribeFileSystems", err)
            return []

    def list_fsx_ontap_volumes(self) -> list["Asset"]:
        volumes = self._fsx.get_paginator("describe_volumes")

        try:
            return [
                self.asset(
                    type=AssetType.FSX_ONTAP_VOLUME,
                    id=volume["VolumeId"],
                    name=volume.get("Name"),
                    state=state,
                    size=volume.get("OntapConfiguration", {}).get("SizeInBytes"),

                    # There are no metrics about files count on an FSX ONTAP volume
                    # in Cloudwatch, and we can't afford mounting the volumes
                    # to count the files, so we just skip this metric.
                    files=None,
                )
                for page in volumes.paginate()
                for volume in page["Volumes"]
                if volume.get("VolumeType") == "ONTAP"
                and (state := volume.get("Lifecycle")) not in ("DELETING", "FAILED")
            ]
        except Exception as err:
            self._log_api_error("fsx:DescribeVolumes", err)
            return []


T = TypeVar("T")


def chunks(input: Iterable[T], chunk_size: int) -> Iterator[list[T]]:
    it = iter(input)
    while chunk := list(itertools.islice(it, chunk_size)):
        yield chunk


def find_name_tag(tags: Optional[list[dict]]) -> Optional[str]:
    return next((tag["Value"] for tag in (tags or []) if tag["Key"] == "Name"), None)


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

    def add_asset(self, type: "AssetType", size: Optional[int]):
        self._per_asset_metrics[type].incr(size)
        self._total_asset_metrics.incr(size)


class AssetsMetrics:
    def __init__(self, label: str):
        self._label = label
        self._size = 0
        self._count = tqdm(
            bar_format=f"{GREEN}{BOLD}{{n_fmt}}{RESET} {{desc}}{RESET}",
            desc=self.description(),
        )

    def description(self):
        size = (
            # Convert bytes to GB
            f" ({GREEN}{BOLD}{self._size / (10**9):_.2f}{RESET} GB)"
            if self._size
            else ""
        )

        return f"{self._label}{size}"

    def incr(self, size: Optional[int]):
        self._count.update(1)
        self._size += size or 0

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
    regions: dict[str, "RichRegion"]

    def __str__(self):
        return f"{self.id} ({self.name})"


@dataclass
class RichRegion:
    name: str
    s3_buckets: list[str]


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
