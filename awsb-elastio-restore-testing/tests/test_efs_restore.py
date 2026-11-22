"""Exercise the CloudFormation Lambda's EFS handoff without AWS credentials or real sleeps."""
import json
import os
import sys
import textwrap
import unittest
from itertools import takewhile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

TEMPLATE = Path(__file__).resolve().parents[1] / "awsb-elastio-rt-simulator.yaml"
A, B = "use1-az1", "use1-az2"
FS, VPC, SG = "fs-00000001", "vpc-00000001", "sg-00000001"
SUBNETS = {"subnet-00000001": A, "subnet-00000002": A, "subnet-00000003": B}
A1, A2, B1 = SUBNETS
RP = "arn:aws:backup:us-east-1:000000000000:recovery-point:example"
PLAN = "arn:aws:backup:us-east-1:000000000000:restore-testing-plan:example"


def embedded_code():
    lines = iter(TEMPLATE.read_text(encoding="utf-8-sig").splitlines(keepends=True))
    marker = next(line for line in lines if line.strip() == "ZipFile: |")
    prefix = marker[:marker.index("ZipFile:")] + " "
    block = takewhile(lambda line: not line.strip() or line.startswith(prefix), lines)
    return compile(textwrap.dedent("".join(block)), str(TEMPLATE), "exec")


class ClientError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.response = {"Error": {"Code": code, "Message": code}}


def target(subnet_id, state):
    return {"FileSystemId": FS, "MountTargetId": "fsmt-" + subnet_id.removeprefix("subnet-"),
            "SubnetId": subnet_id, "VpcId": VPC, "AvailabilityZoneId": SUBNETS[subnet_id],
            "LifeCycleState": state}


class RestoreHandoff(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.delay = {A: 2, B: 7}
        self.born = {}
        self.target_subnets = {A: A1, B: B1}
        self.override_targets = None
        self.race = None
        self.conflicts = []
        self.handoffs = []
        self.efs, self.ec2, self.backup = Mock(), Mock(), Mock()
        self.efs.describe_file_systems.return_value = {"FileSystems": [{"FileSystemId": FS}]}
        self.efs.create_mount_target.side_effect = self.create_target
        self.efs.get_paginator.return_value.paginate.side_effect = self.mount_pages
        self.efs.describe_mount_targets.side_effect = lambda **kw: self.mount_pages(**kw)[0]
        self.ec2.describe_vpcs.return_value = {"Vpcs": [{"VpcId": VPC}]}
        self.ec2.describe_security_groups.return_value = {"SecurityGroups": [{"GroupId": SG}]}
        self.subnets = [{"SubnetId": subnet, "AvailabilityZoneId": zone, "VpcId": VPC,
                         "State": "available", "AvailableIpAddressCount": 4}
                        for subnet, zone in SUBNETS.items()]
        self.subnet_pages = [{"Subnets": self.subnets}]
        self.backup.list_tags.return_value = {"Tags": {"elastio:restore-test": "scan"}}

    def states(self):
        return {zone: "available" if self.now >= start + self.delay[zone] else "creating"
                for zone, start in self.born.items()}

    def create_target(self, *, FileSystemId, SubnetId, SecurityGroups):
        zone = SUBNETS[SubnetId]
        self.assertEqual((FileSystemId, SecurityGroups), (FS, [SG]))
        if zone == self.race:
            self.born.setdefault(zone, self.now)
            self.target_subnets[zone] = SubnetId
        if zone in self.born:
            self.conflicts.append(zone)
            raise ClientError("MountTargetConflict")
        subnet = next(subnet for subnet in self.subnets if subnet["SubnetId"] == SubnetId)
        if subnet["AvailableIpAddressCount"] == 0:
            raise ClientError("NoFreeAddressesInSubnet")
        self.born[zone] = self.now
        self.target_subnets[zone] = SubnetId
        return target(SubnetId, "creating")

    def mount_pages(self, *, FileSystemId):
        if self.override_targets is not None:
            return [{"MountTargets": list(self.override_targets)}]
        return [{"MountTargets": [target(self.target_subnets[zone], state)]}
                for zone, state in self.states().items() if FileSystemId == FS] or [{"MountTargets": []}]

    def sleep(self, seconds):
        if seconds <= 0 or self.now + seconds > 900:
            raise SystemExit("polling exceeded simulated Lambda lifetime")
        self.now += seconds

    def restore(self, resource="EFS", status="COMPLETED"):
        def invoke(**request):
            self.handoffs.append((self.now, self.states(), request))
            return {"StatusCode": 202}

        self.ec2.describe_subnets.return_value = self.subnet_pages[0]
        self.ec2.get_paginator.return_value.paginate.return_value = self.subnet_pages
        clients = {"efs": self.efs, "ec2": self.ec2, "backup": self.backup, "lambda": SimpleNamespace(invoke=invoke)}
        boto = SimpleNamespace(client=lambda name: clients.get(name, Mock()))
        modules = {"boto3": boto, "botocore": SimpleNamespace(), "botocore.exceptions": SimpleNamespace(ClientError=ClientError)}
        arn = ("arn:aws:elasticfilesystem:us-east-1:000000000000:file-system/" + FS
               if resource == "EFS" else "arn:aws:ec2:us-east-1:000000000000:volume/vol-00000001")
        event = {"source": "aws.backup", "detail-type": "Restore Job State Change", "resources": [RP],
                 "detail": {"resourceType": resource, "status": status, "restoreJobId": "job",
                            "restoreTestingPlanArn": PLAN, "createdResourceArn": arn}}
        with patch.dict(sys.modules, modules), patch.dict(os.environ, {"ElastioImportLambdaARN": "import"}, clear=True):
            namespace = {}
            with patch("logging.getLogger", return_value=Mock()):
                exec(embedded_code(), namespace)
            self.reasons = []
            namespace["logger"].exception.side_effect = lambda *args: self.reasons.append(sys.exc_info()[1])
            namespace["find_aws_backup_vault_name"] = lambda rp: "vault"
            namespace["time"] = SimpleNamespace(sleep=self.sleep, monotonic=lambda: self.now)
            namespace["lambda_handler"](event, SimpleNamespace(get_remaining_time_in_millis=lambda: (900 - self.now) * 1000))
        return arn

    def assert_ready_once(self, arn, zones=(A, B)):
        self.assertEqual(len(self.handoffs), 1)
        when, states, request = self.handoffs[0]
        self.assertEqual(states, dict.fromkeys(zones, "available"))
        for zone in zones:
            self.assertGreaterEqual(when, self.born[zone] + self.delay[zone])
        self.assertEqual((request["FunctionName"], request["InvocationType"]), ("import", "Event"))
        payload = json.loads(request["Payload"])
        self.assertEqual((payload["restored_resource_id"], payload["aws_backup_rp_arn"]), (FS, RP))
        self.assertEqual(payload["iscan"]["user_data"].split(",")[2:], [PLAN, "job", RP, arn])

    def test_duplicate_subnets_then_next_zone(self):
        arn = self.restore()
        self.assertEqual(set(self.born), {A, B})
        self.assertEqual(self.conflicts, [])
        self.assertEqual(self.efs.create_mount_target.call_count, 2)
        self.assert_ready_once(arn)

    def test_exhausted_first_subnet_uses_second_in_same_zone(self):
        self.subnets[0]["AvailableIpAddressCount"] = 0
        arn = self.restore()
        self.assertCountEqual([call.kwargs["SubnetId"] for call in self.efs.create_mount_target.call_args_list], [A2, B1])
        self.assert_ready_once(arn)

    def test_capacity_lost_after_discovery_tries_next_subnet_in_same_zone(self):
        def create(**kwargs):
            if kwargs["SubnetId"] == A1:
                self.subnets[0]["AvailableIpAddressCount"] = 0
            return self.create_target(**kwargs)

        self.efs.create_mount_target.side_effect = create
        arn = self.restore()
        attempted = [call.kwargs["SubnetId"] for call in self.efs.create_mount_target.call_args_list]
        self.assertCountEqual(attempted, [A1, A2, B1])
        self.assertLess(attempted.index(A1), attempted.index(A2))
        self.assert_ready_once(arn)

    def test_other_create_error_stops_without_fallback(self):
        self.efs.create_mount_target.side_effect = ClientError("AccessDenied")
        self.restore()
        self.assertEqual(self.efs.create_mount_target.call_count, 1)
        self.assertEqual(self.handoffs, [])
        self.assertTrue(any("AccessDenied" in str(e) for e in self.reasons))

    def test_concurrent_creation_already_available_under_tight_budget(self):
        self.now = 881  # 4s prep budget left (<= 5s poll); concurrent target is already available
        self.delay = {A: 0, B: 0}
        self.race = A
        self.born = {B: 0}
        arn = self.restore()
        self.assertEqual(self.conflicts, [A])
        self.assertEqual(self.now, 881)
        self.assert_ready_once(arn)

    def test_new_target_ready_on_first_describe_under_tight_budget(self):
        self.now = 881
        self.delay[A] = 0
        self.born = {B: 0}
        arn = self.restore()
        self.assertGreaterEqual(self.efs.get_paginator.return_value.paginate.call_count, 2)
        self.assertEqual(self.now, 881)
        self.assert_ready_once(arn)

    def test_existing_targets_on_separate_pages_and_deleted_ignored(self):
        self.subnet_pages = [{"Subnets": self.subnets[:2]}, {"Subnets": self.subnets[2:]}]
        self.born = {B: 0}
        calls = 0
        def pages_with_deleted(*, FileSystemId):
            nonlocal calls
            calls += 1
            if calls == 1:
                return [
                    {"MountTargets": [target(A1, "deleted")]},
                    {"MountTargets": [target(B1, "creating")]},
                ]
            return self.mount_pages(FileSystemId=FileSystemId)
        self.efs.get_paginator.return_value.paginate.side_effect = pages_with_deleted
        arn = self.restore()
        self.ec2.get_paginator.assert_called_once_with("describe_subnets")
        self.ec2.get_paginator.return_value.paginate.assert_called_once_with(
            Filters=[{"Name": "vpc-id", "Values": [VPC]}])
        self.assertEqual({c.args for c in self.efs.get_paginator.call_args_list}, {("describe_mount_targets",)})
        self.efs.create_mount_target.assert_called_once_with(FileSystemId=FS, SubnetId=A1, SecurityGroups=[SG])
        self.assert_ready_once(arn)

    def test_other_vpc_mount_target_fails_immediately_without_polling(self):
        self.override_targets = [dict(target(A1, "available"), VpcId="vpc-other", SubnetId="subnet-99999999")]
        self.restore()
        self.assertEqual(self.now, 0)
        self.efs.create_mount_target.assert_not_called()
        self.assertEqual(self.handoffs, [])
        self.assertTrue(any(isinstance(e, RuntimeError) and "vpc-other" in str(e) for e in self.reasons))

    def test_deleting_mount_target_fails_immediately_without_polling(self):
        self.override_targets = [target(A1, "deleting"), target(B1, "available")]
        self.restore()
        self.assertEqual(self.now, 0)
        self.assertEqual(self.handoffs, [])
        self.assertTrue(any(isinstance(e, RuntimeError) and "deleting" in str(e) for e in self.reasons))

    def test_subnet_identifies_targets_when_optional_vpc_and_zone_are_absent(self):
        self.born = {A: -20, B: -20}
        self.override_targets = [target(A2, "available"), target(B1, "available")]
        for row in self.override_targets:
            del row["VpcId"], row["AvailabilityZoneId"]
        self.assert_ready_once(self.restore())
        self.efs.create_mount_target.assert_not_called()

    def test_unknown_subnet_cannot_confirm_vpc_membership(self):
        other = target(B1, "available")
        del other["VpcId"]
        other["SubnetId"] = "subnet-99999999"
        self.override_targets = [target(A1, "available"), other]
        self.restore()
        self.assertEqual(self.handoffs, [])
        self.efs.create_mount_target.assert_not_called()
        self.assertTrue(any(other["SubnetId"] in str(e) for e in self.reasons))

    def test_zone_disagreement_with_subnet_stops_dispatch(self):
        self.override_targets = [target(A1, "available"), dict(target(B1, "available"), AvailabilityZoneId=A)]
        self.restore()
        self.assertEqual(self.handoffs, [])
        self.efs.create_mount_target.assert_not_called()
        self.assertTrue(self.reasons)

    def test_exhausted_zone_without_target_stops_dispatch(self):
        self.subnets[2]["AvailableIpAddressCount"] = 0
        self.born = {A: -20}
        self.restore()
        self.assertEqual(self.handoffs, [])
        self.efs.create_mount_target.assert_not_called()
        self.assertTrue(any(B in str(e) for e in self.reasons))

    def test_exhausted_zone_with_creating_target_never_becomes_ready(self):
        self.subnets[2]["AvailableIpAddressCount"] = 0
        self.born = {A: -20, B: 0}
        self.delay[B] = float("inf")
        self.restore()
        self.assertEqual(self.handoffs, [])
        self.efs.create_mount_target.assert_not_called()
        self.assertTrue(any(isinstance(e, TimeoutError) and B in str(e) for e in self.reasons))

    def test_exhausted_zone_with_existing_target_becomes_ready(self):
        self.subnets[2]["AvailableIpAddressCount"] = 0
        self.born = {A: -20, B: 0}
        self.assert_ready_once(self.restore())
        self.efs.create_mount_target.assert_not_called()

    def test_existing_targets_need_no_new_ips(self):
        for subnet in self.subnets:
            subnet["AvailableIpAddressCount"] = 0
        self.born = {A: -20, B: -20}
        self.assert_ready_once(self.restore())
        self.efs.create_mount_target.assert_not_called()

    def test_existing_one_zone_target_needs_no_new_ip(self):
        self.efs.describe_file_systems.return_value["FileSystems"][0]["AvailabilityZoneId"] = B
        self.subnets[2]["AvailableIpAddressCount"] = 0
        self.born = {B: -20}
        self.assert_ready_once(self.restore(), (B,))
        self.efs.create_mount_target.assert_not_called()

    def test_one_zone_without_matching_subnet_skips_dispatch(self):
        self.efs.describe_file_systems.return_value["FileSystems"][0]["AvailabilityZoneId"] = "use1-az9"
        self.restore()
        self.efs.create_mount_target.assert_not_called()
        self.assertEqual(self.handoffs, [])
        self.assertTrue(any(isinstance(e, ValueError) and "use1-az9" in str(e) for e in self.reasons))

    def test_missing_security_group_skips_creation_and_dispatch(self):
        self.ec2.describe_security_groups.side_effect = ClientError("UnauthorizedOperation")
        self.restore()
        self.efs.create_mount_target.assert_not_called()
        self.assertEqual(self.handoffs, [])
        self.assertTrue(any(isinstance(e, ValueError) and "security group" in str(e) for e in self.reasons))

    def test_second_zone_never_ready(self):
        self.subnets.pop(1)
        self.delay[B] = float("inf")
        self.restore()
        self.assertEqual(set(self.born), {A, B})
        self.assertEqual(self.handoffs, [])
        self.backup.put_restore_validation_result.assert_not_called()
        self.assertTrue(any(isinstance(e, TimeoutError) and B in str(e) and "creating" in str(e) for e in self.reasons))

    def test_one_zone_uses_only_its_own_subnet(self):
        self.efs.describe_file_systems.return_value["FileSystems"][0]["AvailabilityZoneId"] = B
        self.assert_ready_once(self.restore(), (B,))

    def test_insufficient_time_to_provision(self):
        self.now = 890
        self.restore()
        self.efs.create_mount_target.assert_not_called()
        self.assertEqual(self.handoffs, [])

    def test_empty_subnets(self):
        self.subnets.clear()
        self.restore()
        self.assertEqual(self.handoffs, [])

    def test_nonterminal_and_non_efs_controls(self):
        self.restore(status="RUNNING")
        self.assertEqual(self.handoffs, [])
        self.restore(resource="EBS")
        self.assertEqual(len(self.handoffs), 1)
        self.assertEqual(json.loads(self.handoffs[0][2]["Payload"])["restored_resource_id"], "vol-00000001")
        self.efs.get_paginator.assert_not_called()
        self.efs.create_mount_target.assert_not_called()


if __name__ == "__main__":
    unittest.main()
