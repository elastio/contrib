from dataclasses import dataclass, asdict, is_dataclass
from datetime import datetime
from typing import Iterable, Optional, TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from mypy_boto3_ec2.type_defs import SubnetTypeDef, InstanceTypeDef
    from mypy_boto3_ecs.type_defs import TaskTypeDef

import json
import os
import time
import itertools
import boto3
import botocore

cfn = boto3.client('cloudformation')
ec2 = boto3.client('ec2')
ecs = boto3.client('ecs')
sfn = boto3.client('stepfunctions')

NAT_CFN_PREFIX = os.environ['NAT_CFN_PREFIX']
NAT_CFN_TEMPLATE_URL = os.environ['NAT_CFN_TEMPLATE_URL']
STATE_MACHINE_ARN = os.environ['STATE_MACHINE_ARN']
LAMBDA_NAME = os.environ['AWS_LAMBDA_FUNCTION_NAME']
NAT_GATEWAY_SCOPE = os.environ.get('NAT_GATEWAY_SCOPE', 'vpc')

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

def to_json(value):
    return json.dumps(value, cls=AnyClassEncoder)

def print_json(label: str, value):
    print(to_json({ label: value }))

type AnyEvent = Ec2Event | EcsEvent | ScheduleEvent
type WorkloadEvent = Ec2Event | EcsEvent

@dataclass
class Ec2Event:
    time: datetime
    ec2_instance_id: str

@dataclass
class EcsEvent:
    time: datetime
    ecs_task_arn: str
    ecs_cluster_arn: str
    subnet_id: str
    status: str

@dataclass
class ScheduleEvent:
    pass


def lambda_handler(event, _context):
    print_json("boto3_version", boto3.__version__)
    print_json("botocore_version", botocore.__version__)
    print_json("event", event)

    match event:
        case { 'elastio_scheduled_cleanup': True }:
            cleanup_nat(ScheduleEvent())

        case { 'source': 'aws.ecs' }:
            handle_raw_ecs_event(event)

        case { 'source': 'aws.ec2' }:
            handle_raw_ec2_event(event)

        case _:
            raise Exception(f"Unknown event received")

def handle_raw_ecs_event(event: dict):
    detail = event['detail']
    ecs_task_status = detail['lastStatus']

    subnet_id = get_ecs_task_subnet_id(detail)

    if subnet_id is None:
        raise Exception(f"No subnet ID information in the ECS event")

    ecs_event = EcsEvent(
        time=datetime.fromisoformat(event['time']),
        ecs_task_arn=detail['taskArn'],
        ecs_cluster_arn=detail['clusterArn'],
        subnet_id=subnet_id,
        status=ecs_task_status,
    )

    match ecs_task_status:
        case 'STOPPED':
            cleanup_nat(ecs_event)
        case 'PROVISIONING':
            ensure_nat(ecs_event)
        case _:
            raise Exception(f"Unexpected ECS task status: {ecs_task_status}")

def handle_raw_ec2_event(event: dict):
    detail = event['detail']
    ec2_instance_state = detail['state']
    ec2_event = Ec2Event(
        time=datetime.fromisoformat(event['time']),
        ec2_instance_id=detail['instance-id'],
    )

    match ec2_instance_state:
        case 'pending':
            ensure_nat(ec2_event)
        case 'stopped' | 'terminated':
            cleanup_nat(ec2_event)
        case _:
            raise Exception(f"Unexpected EC2 instance state: {ec2_instance_state}")

def get_ecs_task_subnet_id(ecs_task: 'TaskTypeDef') -> Optional[str]:
    eni = next(
        (
            attachment
            for attachment in ecs_task['attachments']
            if (attachment['type'] == 'eni' or attachment['type'] == 'ElasticNetworkInterface')
        ),
        None
    )

    if eni is None:
        return None;

    return next(
        (
            detail['value']
            for detail in eni['details']
            if detail['name'] == 'subnetId'
        ),
        None
    )


def request(client, operation, query, **kwargs):
    """
    Sends a paginated request to AWS, filters the response with a JMESPath
    query and returns a list.
    """
    paginator = client.get_paginator(operation)
    page_iter = paginator.paginate(**kwargs)
    filtered = page_iter.search(query)
    return list(filtered)

def get_workload(event: WorkloadEvent) -> Optional['Workload']:
    if isinstance(event, Ec2Event):
        return get_ec2_workload(event)

    if isinstance(event, EcsEvent):
        return get_ecs_workload(event)

    raise Exception(f"Unknown workload event type: {event}")

def get_ec2_workload(event: Ec2Event) -> Optional['Ec2Workload']:
    response = ec2.describe_instances(
        InstanceIds=[event.ec2_instance_id],
    )

    print_json("ec2_workload_instance_response", response)

    ec2_instance = response['Reservations'][0]['Instances'][0]

    is_elastio_resource = any(
        tag['Key'] == 'elastio:resource' and tag['Value'] == 'true'
        for tag in ec2_instance['Tags']
    )

    if not is_elastio_resource:
        print(
            f"No 'elastio:resource=true' tag found on EC2 instance "
            f"{event.ec2_instance_id}; no action taken."
        )
        return None

    return Ec2Workload.from_aws_api(ec2_instance)

def get_ecs_workload(event: EcsEvent) -> Optional['EcsWorkload']:
    response = ec2.describe_subnets(
        SubnetIds=[event.subnet_id],
    )

    print_json("ecs_workload_subnet_response", response)

    subnet = response['Subnets'][0]

    return EcsWorkload(
        subnet_id=event.subnet_id,
        vpc_id=subnet['VpcId'],
        az=subnet['AvailabilityZone'],
        ecs_task_arn=event.ecs_task_arn,
        ecs_cluster_arn=event.ecs_cluster_arn,
        status=event.status,
    )


def ensure_nat(event: WorkloadEvent):
    workload = get_workload(event)

    print_json("discovered_workload", workload)

    if workload is None:
        return

    if workload.vpc_id is None:
        raise Exception(f"VPC ID is not known for the workload: {to_json(workload)}")

    if workload.subnet_id is None:
        raise Exception(f"Subnet ID is not known for the workload: {to_json(workload)}")

    subnets = {sn['SubnetId']: sn for sn in request(
        ec2,
        'describe_subnets',
        'Subnets',
        Filters=[{'Name': 'vpc-id', 'Values': [workload.vpc_id]}],
    )}
    print_json("subnets", subnets)

    route_tables = {rt['RouteTableId']: rt for rt in request(
        ec2,
        'describe_route_tables',
        'RouteTables',
        Filters=[{'Name': 'vpc-id', 'Values': [workload.vpc_id]}],
    )}
    print_json("route_tables", route_tables)

    main_route_table_id = None
    subnet_to_route_table = {}

    for rt_id, rt in route_tables.items():
        for assoc in rt['Associations']:
            if assoc['Main']:
                main_route_table_id = rt_id
            subnet_id = assoc.get('SubnetId')
            if subnet_id:
                subnet_to_route_table[subnet_id] = rt_id

    for subnet_id in subnets:
        if subnet_id not in subnet_to_route_table:
            subnet_to_route_table[subnet_id] = main_route_table_id

    public_subnets_ids = set(get_public_subnets(subnet_to_route_table, route_tables))
    print_json("public_subnets_ids", public_subnets_ids)

    workload_route_table_id = subnet_to_route_table[workload.subnet_id]
    workload_route_table = route_tables[workload_route_table_id]

    if not public_subnets_ids:
        print(f"No public subnets found in {workload.vpc_id}; exiting")
        return

    if workload.subnet_id in public_subnets_ids:
        if not subnets[workload.subnet_id]['MapPublicIpOnLaunch']:
            print(
                "WARN: Workload was launched in a public subnet, but the subnet has"
                " `MapPublicIpOnLaunch` set to `false`. In order for Elastio workers"
                " to be able to access internet, `MapPublicIpOnLaunch` must be set to `true`."
            )
        else:
            print("Workload is running in a public subnet; exiting")
        return

    nat_deployments = list(get_nat_deployments(subnets))
    print_json("nat_deployments", nat_deployments)

    all_traffic_route = get_all_traffic_route(workload_route_table)

    if all_traffic_route is not None:
        nat_gateway_id = all_traffic_route.get('NatGatewayId', None)
        if nat_gateway_id is None:
            print(
                f"Route table already has a route for 0.0.0.0/0 "
                f"which is not a NAT gateway. Exiting. Route: {to_json(all_traffic_route)}"
            )
            return

        if not is_nat_managed_by_us(nat_deployments, nat_gateway_id):
            print(
                f"Route table already has a route for 0.0.0.0/0 "
                f"which isn't managed by us. Exiting. Route: {to_json(all_traffic_route)}"
            )
            return

    nat_subnet_id = choose_subnet_for_nat(
        nat_deployments,
        subnets,
        public_subnets_ids,
        workload,
    )

    if nat_subnet_id is None:
        print(
            "Unable to find a public subnet for NAT in "
            f"the {NAT_GATEWAY_SCOPE} scope; exiting"
        )
        return

    print(f"Chose the following public subnet for NAT: {nat_subnet_id}")

    stack_name = f"{NAT_CFN_PREFIX}{nat_subnet_id}"

    if not is_stack_deployed(stack_name):
        print(f"No existing stack '{stack_name}' found, deploying new stack")
        deploy_nat_stack(stack_name, nat_subnet_id, workload_route_table_id)
    else:
        print(f"Stack {stack_name} already exists or is in progress; nothing more to do.")

def is_nat_managed_by_us(nat_deployments: list['NatDeployment'], suspect_nat_gateway_id: str) -> bool:
    nat_deployment = next(
        (
            nat_deployment for nat_deployment in nat_deployments
            if nat_deployment.nat_gateway_id == suspect_nat_gateway_id
        ),
        None
    )

    if nat_deployment is None:
        print(f"NAT gateway {suspect_nat_gateway_id} is not managed by Elastio.")
        return False

    print(f"NAT gateway {suspect_nat_gateway_id} is managed by Elastio stack: {to_json(nat_deployment)}")

    return True

def get_stack_status(stack_name):
    try:
        stacks = request(
            cfn,
            'describe_stacks',
            'Stacks',
            StackName=stack_name,
        )

        print_json("existing_nat_cfn_stack", stacks[0])

        return stacks[0]['StackStatus']
    except cfn.exceptions.ClientError as e:
        if 'does not exist' in str(e):
            print(f"Stack with a name {stack_name} does not exist.")
        else:
            print(f"Error describing stack {stack_name}: {repr(e)}")
            print(f"Assuming the stack {stack_name} does not exist.")
        return None


def is_stack_deployed(stack_name):
    stack_status = get_stack_status(stack_name)

    if stack_status == 'DELETE_IN_PROGRESS':
        print(f"The stack {stack_name} is being deleted, waiting until the deletion completes.")
        while True:
            time.sleep(5)
            stack_status = get_stack_status(stack_name)
            if stack_status != 'DELETE_IN_PROGRESS':
                break

    if stack_status is None:
        return False

    print(f"Stack {stack_name} is deployed and has status {stack_status}.")
    return True


def deploy_nat_stack(stack_name, subnet_id, route_table_id):
    try:
        response = cfn.create_stack(
            StackName=stack_name,
            TemplateURL=NAT_CFN_TEMPLATE_URL,
            OnFailure='DELETE',
            Parameters=[
                {
                    'ParameterKey': 'PublicSubnetId',
                    'ParameterValue': subnet_id,
                },
                {
                    'ParameterKey': 'PrivateSubnetRouteTableId',
                    'ParameterValue': route_table_id,
                },
            ],
            Tags=[
                {
                    'Key': 'elastio:resource',
                    'Value': 'true',
                },
                {
                    'Key': 'elastio:created-by',
                    'Value': f'lambda:{LAMBDA_NAME}',
                }
            ]
        )
        print(f"Stack creation initiated for {stack_name}: {to_json(response)}")
    except cfn.exceptions.AlreadyExistsException:
        print(f"Stack {stack_name} already exists")


def choose_subnet_for_nat(
    nat_deployments: list['NatDeployment'],
    subnets: dict,
    public_subnets_ids: set[str],
    workload: 'Workload',
):
    for nat_deployment in nat_deployments:
        if (
            nat_deployment.vpc_id == workload.vpc_id and
            (
                NAT_GATEWAY_SCOPE == 'vpc' or
                nat_deployment.az == workload.az
            )
        ):
            print(f"Found already existing NAT deployment: {to_json(nat_deployment)}")
            return nat_deployment.subnet_id

    scope = render_scope(workload.vpc_id, workload.az)

    print(f"No existing deployments found for {scope}")

    return next(
        (
            subnet_id
            for subnet_id in sorted(list(public_subnets_ids))
            if (
                NAT_GATEWAY_SCOPE == 'vpc' or
                subnets[subnet_id]['AvailabilityZone'] == workload.az
            )
        ),
        None
    )

def get_public_subnets(subnet_to_route_table, route_tables):
    for subnet_id, rt_id in subnet_to_route_table.items():
        route_table = route_tables[rt_id]

        route = get_all_traffic_route(route_table)
        if route is None:
            continue

        if not route['State'] == 'active':
            continue

        gw_id = route.get('GatewayId')
        if gw_id is None or not gw_id.startswith('igw-'):
            continue

        yield subnet_id


def get_all_traffic_route(route_table):
    for route in route_table['Routes']:
        if route.get('DestinationCidrBlock') == '0.0.0.0/0':
            return route
    return None

def list_workloads(subnets: dict[str, 'SubnetTypeDef']) -> dict[str, 'Workload']:
    workloads: dict[str, 'Workload'] = {
        **list_ec2_instances(),
        **list_ecs_tasks(subnets),
    }

    print_json("discovered_workloads", workloads)

    return workloads

def list_ec2_instances() -> dict[str, 'Ec2Workload']:
    ec2_instances = list(
        ec2
        .get_paginator('describe_instances')
        .paginate(
            Filters=[
                { 'Name': 'tag:elastio:resource', 'Values': ['true'] }
            ]
        )
    )

    print_json('ec2_instances', ec2_instances)

    return {
        instance['InstanceId']: Ec2Workload(
            subnet_id=instance.get('SubnetId'),
            vpc_id=instance.get('VpcId'),
            az=az,
            ec2_instance_id=instance['InstanceId'],
            state=instance['State']['Name'],
        )
        for page in ec2_instances
        for reservation in page.get('Reservations', [])
        for instance in reservation.get('Instances', [])
        if (az := instance.get('Placement', {}).get('AvailabilityZone')) is not None
    }

def list_ecs_tasks(subnets: dict[str, 'SubnetTypeDef']) -> dict[str, 'EcsWorkload']:
    return {
        task['taskArn']: EcsWorkload(
            subnet_id=subnet_id,
            vpc_id=subnets[subnet_id]['VpcId'],
            az=task['availabilityZone'],
            ecs_task_arn=task['taskArn'],
            ecs_cluster_arn=task['clusterArn'],
            status=task['lastStatus'],
        )
        for task in list_ecs_tasks_impl()
        if (subnet_id := get_ecs_task_subnet_id(task)) in subnets
    }

def list_ecs_tasks_impl():
    ecs_clusters = [
        cluster_arn
        for cluster in ecs.get_paginator('list_clusters').paginate()
        for cluster_arn in cluster['clusterArns']
    ]

    print_json("ecs_clusters", ecs_clusters)

    ecs_clusters_to_tasks = {
        cluster_arn: task['taskArns']
            for cluster_arn in ecs_clusters
            for task in (
                ecs
                .get_paginator('list_tasks')
                .paginate(cluster=cluster_arn, launchType='FARGATE')
            )
    }

    print_json("ecs_clusters_to_tasks", ecs_clusters_to_tasks)

    for cluster_arn, task_arns in ecs_clusters_to_tasks.items():
        if len(task_arns) == 0:
            continue

        for task_arns_chunk in chunks(task_arns, 100):
            ecs_tasks = ecs.describe_tasks(
                cluster=cluster_arn,
                tasks=task_arns_chunk,
                include=['TAGS'],
            )

            print_json("ecs_describe_tasks_response", ecs_tasks)

            failures = ecs_tasks['failures']

            if len(failures) > 0:
                print(f"WARN: failed to describe some ECS tasks: {to_json(failures)}")

            yield from (
                task
                for task in ecs_tasks['tasks']
                if any(
                    tag.get('key') == 'elastio:resource' and tag.get('value') == 'true'
                    for tag in task.get('tags', [])
                )
            )

def cleanup_nat(event: AnyEvent):
    subnets = {
        subnet['SubnetId']: subnet
        for page in ec2.get_paginator('describe_subnets').paginate()
        for subnet in page['Subnets']
    }
    print_json("subnets", subnets)

    nat_deployments = list(get_nat_deployments(subnets))
    print_json("nat_deployments", nat_deployments)

    if len(nat_deployments) == 0:
        print("No NAT Gateway deployments found; nothing to do.")
        return

    workloads = list_workloads(subnets)

    try:
        pending_cleanups = get_pending_cleanups(
            subnets,
            workloads,
            event
        )
    except Exception as e:
        print(f"Failed to list pending cleanups; assuming there are none: {repr(e)}")
        pending_cleanups = PendingCleanups()

    for nat_deployment in nat_deployments:
        nat_vpc_id = nat_deployment.vpc_id
        nat_az = nat_deployment.az

        scope = render_scope(nat_vpc_id, nat_az)

        if pending_cleanups.contains(nat_vpc_id, nat_az):
            print(f"There is a more recent cleanup pending for {scope}; skipping.")
            continue

        active_workloads = (
            workload for workload in workloads.values()
            if workload.is_active_in_scope(nat_vpc_id, nat_az)
        )

        active_workload = next(active_workloads, None)

        if active_workload is not None:
            print(
                f"Found potentially active elastio workload in {scope};"
                f" skipping NAT gateway stack deletion."
                f" Workload: {to_json(active_workload)}"
            )
            continue

        print(f"No active elastio workloads found in {scope}")

        stack_name = f"{NAT_CFN_PREFIX}{nat_deployment.subnet_id}"

        if is_stack_needs_to_be_deleted(stack_name):
            print(f"Initiating deletion of NAT gateway stack '{stack_name}' for {scope}.")
            delete_nat_gateway_stack(stack_name)


def get_pending_cleanups(
    subnets: dict[str, 'SubnetTypeDef'],
    workloads: dict[str, 'Workload'],
    event: AnyEvent
):
    """
    Returns a map { vpc_id => [availability_zone] } for which there are more recent
    pending cleanup tasks in the state machine, currently waiting for the quiescent period.
    In other words, it returns availability zones of VPCs we should skip the cleanup for,
    because they will be soon handled by a more recent event.
    """
    execution_arns = request(
        sfn,
        'list_executions',
        'executions[].executionArn',
        stateMachineArn=STATE_MACHINE_ARN,
        statusFilter='RUNNING',
    )

    # This is the set of cleanups that are more recent than the current event
    # that we should skip in this run.
    pending_cleanups = PendingCleanups()

    print(f"Discovered SFN execution ARNs: {to_json(execution_arns)}")

    for execution_arn in execution_arns:
        execution = sfn.describe_execution(
            executionArn=execution_arn,
        )

        print(f"Discovered SFN execution: {to_json(execution)}")

        exec_input = json.loads(execution['input'])

        sfn_time = datetime.fromisoformat(exec_input['time'])

        workload_id = None
        workload_az = None
        match exec_input:
            case { 'source': 'aws.ecs', 'detail': detail }:
                workload_id = detail['taskArn']
                workload_az = detail['availabilityZone']

            case { 'source': 'aws.ec2', 'detail': { 'instance-id': instance_id } }:
                workload_id = instance_id
                workload = workloads.get(instance_id)
                if workload is not None:
                    workload_az = workload.az
                elif NAT_GATEWAY_SCOPE == 'az':
                    print(
                        f"Can't determine the AZ of the EC2 instance from the event "
                        f"in SFN, because EC2 instance info is no longer returned from "
                        f"the DescribeInstances API: {instance_id}. Ignoring it."
                    )
                    continue
            case _:
                print(f"WARN: unknown state machine input. Ignoring it: {to_json(exec_input)}")
                continue

        # skip the execution that invoked the currently running lambda
        if (
            (isinstance(event, Ec2Event) and event.ec2_instance_id == workload_id)
            or
            (isinstance(event, EcsEvent) and event.ecs_task_arn == workload_id)
        ):
            print(f"Current SFN execution: {execution["executionArn"]}")
            continue


        # if the event input of the SFN execution is older than one we
        # are currently handling, then we should do the cleanup, so
        # we don't add the scope to the pending cleanups set
        if not isinstance(event, ScheduleEvent) and event.time >= sfn_time:
            print(
                f"This lambda run ({event.time}) overtakes the older scheduled "
                f"SFN execution for an event ({sfn_time}): {execution_arn}"
            )
            continue

        for subnet in subnets.values():
            vpc_id = subnet['VpcId']
            subnet_az = subnet['AvailabilityZone']

            if NAT_GATEWAY_SCOPE == 'az' and subnet_az != workload_az:
                continue

            pending_cleanups.add(vpc_id, subnet_az)

        if NAT_GATEWAY_SCOPE == 'vpc':
            # The workload could be in any subnet in any vpc.
            # We added all vpc/az pairs to pending cleanups already
            # on the first iteration, so we can exit early
            break

    print_json("pending_cleanups", pending_cleanups)

    return pending_cleanups


def is_stack_needs_to_be_deleted(stack_name):
    stack_status = get_stack_status(stack_name)

    if stack_status == 'CREATE_IN_PROGRESS':
        print(f"The stack {stack_name} is being created, waiting until the creation completes.")
        while True:
            time.sleep(5)
            stack_status = get_stack_status(stack_name)
            if stack_status != 'CREATE_IN_PROGRESS':
                break

    if stack_status is None:
        return False

    if stack_status == 'DELETE_IN_PROGRESS':
        print(f"Stack {stack_name} is in the process of being deleted.")
        return False

    print(f"Stack {stack_name} exists and has status {stack_status}.")
    return True


def delete_nat_gateway_stack(stack_name):
    try:
        response = cfn.delete_stack(StackName=stack_name)
        print(f"Stack deletion initiated for {stack_name}: {to_json(response)}")
    except cfn.exceptions.ClientError as e:
        if 'does not exist' in str(e):
            print(f"Stack {stack_name} does not exist anymore")
        else:
            print(f"Failed to delete stack {stack_name}: {repr(e)}")


def get_nat_deployments(subnets):
    nat_gateways = request(
        ec2,
        'describe_nat_gateways',
        'NatGateways',
        Filters=[
            {
                'Name': 'tag-key',
                'Values': ['elastio:nat-provision-stack-id']
            },
            {
                'Name': 'state',
                'Values': ['pending', 'failed', 'available', 'deleting'],
            },
        ],
    )
    for nat in nat_gateways:
        nat_gateway_id = nat['NatGatewayId']
        subnet_id = nat['SubnetId']
        subnet = subnets.get(subnet_id)
        if subnet is None:
            continue
        vpc_id = subnet['VpcId']
        az = subnet['AvailabilityZone']
        stack_id = next(
            tag['Value'] for tag in nat['Tags']
            if tag['Key'] == 'elastio:nat-provision-stack-id'
        )
        yield NatDeployment(nat_gateway_id, stack_id, vpc_id, subnet_id, az)

def render_scope(vpc, az):
    return (
        vpc
        if NAT_GATEWAY_SCOPE == 'vpc'
        else f'{vpc}/{az}'
    )

@dataclass
class NatDeployment:
    nat_gateway_id: str
    stack_id: str
    vpc_id: str
    subnet_id: str
    az: str

class PendingCleanups:
    def __init__(self):
        self.vpc_id_to_zones = {}

    def __str__(self):
        return str(self.vpc_id_to_zones)

    def add(self, vpc_id: str, az: str):
        azs = self.vpc_id_to_zones.pop(vpc_id, set())
        azs.add(az)
        self.vpc_id_to_zones[vpc_id] = azs

    def contains(self, vpc_id: str, az: str):
        azs = self.vpc_id_to_zones.get(vpc_id)
        return (not (azs is None)) and (NAT_GATEWAY_SCOPE == 'vpc' or az in azs)

type Workload = Ec2Workload | EcsWorkload

@dataclass
class Ec2Workload:
    vpc_id: Optional[str]
    subnet_id: Optional[str]
    az: str
    ec2_instance_id: str
    state: str

    @staticmethod
    def from_aws_api(ec2_instance: 'InstanceTypeDef') -> 'Ec2Workload':
        return Ec2Workload(
            vpc_id=ec2_instance.get('VpcId'),
            subnet_id=ec2_instance.get('SubnetId'),
            az=ec2_instance['Placement']['AvailabilityZone'],
            ec2_instance_id=ec2_instance['InstanceId'],
            state=ec2_instance['State']['Name'],
        )

    def is_active_in_scope(self, vpc_id: str, az: str) -> bool:
        active_states = ('pending', 'running', 'stopping', 'shutting-down')

        return (
            self.state in active_states and
            (NAT_GATEWAY_SCOPE == 'vpc' or self.az == az) and (
                # VpcId and SubnetId are not always present in the EC2 instance.
                # It isn't present in case if the EC2 instance is in shutting-down
                # state, for example (seen during testing). Maybe there are some other cases
                # where VpcId isn't present, so we gracefully consider such instances as
                # potentially active in the given VPC.
                self.vpc_id == None
                or
                self.vpc_id == vpc_id
            )
        )

@dataclass
class EcsWorkload:
    vpc_id: str
    subnet_id: str
    az: str
    ecs_task_arn: str
    ecs_cluster_arn: str
    status: str

    def is_active_in_scope(self, vpc_id: str, az: str) -> bool:
        return (
            self.status not in ('STOPPED', 'DELETED') and
            self.vpc_id == vpc_id and
            (NAT_GATEWAY_SCOPE == 'vpc' or self.az == az)
        )

def chunks[T](input: Iterable[T], chunk_size: int):
    it = iter(input)
    return iter(lambda: list(itertools.islice(it, chunk_size)), [])
