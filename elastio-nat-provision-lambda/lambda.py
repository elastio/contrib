from dataclasses import dataclass
from datetime import datetime
import json
import os
import time

import boto3
import botocore

cfn = boto3.client('cloudformation')
ec2 = boto3.client('ec2')
sfn = boto3.client('stepfunctions')

NAT_CFN_PREFIX = os.environ['NAT_CFN_PREFIX']
NAT_CFN_TEMPLATE_URL = os.environ['NAT_CFN_TEMPLATE_URL']
STATE_MACHINE_ARN = os.environ['STATE_MACHINE_ARN']


def lambda_handler(event, _context):
    print(f"boto3 version: {boto3.__version__}")
    print(f"botocore version: {botocore.__version__}")
    print("event:", event)

    if bool(event.get('elastio_scheduled_cleanup')):
        cleanup_nat(None, None)
    else:
        instance_id = event['detail']['instance-id']
        instance_state = event['detail']['state']
        event_time = datetime.fromisoformat(event['time'])

        if instance_state == 'pending':
            ensure_nat(instance_id)
        elif instance_state in ('stopped', 'terminated'):
            cleanup_nat(instance_id, event_time)


def request(client, operation, query, **kwargs):
    """
    Sends a paginated request to AWS, filters the response with a JMESPath
    query and returns a list.
    """
    paginator = client.get_paginator(operation)
    page_iter = paginator.paginate(**kwargs)
    filtered = page_iter.search(query)
    return list(filtered)


def ensure_nat(instance_id):
    instance = request(
        ec2,
        'describe_instances',
        'Reservations[].Instances[]',
        InstanceIds=[instance_id],
    )[0]

    print("instance:", instance)

    instance_vpc_id = instance['VpcId']
    instance_subnet_id = instance['SubnetId']
    instance_tags = instance['Tags']

    if not any(
            tag['Key'] == 'elastio:resource' and tag['Value'] == 'true'
            for tag in instance_tags
    ):
        print(f"No matching elastio:resource tag found on instance {instance_id}; no action taken.")
        return

    subnets = {sn['SubnetId']: sn for sn in request(
        ec2,
        'describe_subnets',
        'Subnets',
        Filters=[{'Name': 'vpc-id', 'Values': [instance_vpc_id]}],
    )}
    print("subnets:", subnets)

    route_tables = {rt['RouteTableId']: rt for rt in request(
        ec2,
        'describe_route_tables',
        'RouteTables',
        Filters=[{'Name': 'vpc-id', 'Values': [instance_vpc_id]}],
    )}
    print("route_tables:", subnets)

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
    print("public_subnets_ids:", public_subnets_ids)

    instance_route_table_id = subnet_to_route_table[instance_subnet_id]
    instance_route_table = route_tables[instance_route_table_id]

    if not public_subnets_ids:
        print(f"No public subnets found in {instance_vpc_id}; exiting")
        return

    if instance_subnet_id in public_subnets_ids:
        if not subnets[instance_subnet_id]['MapPublicIpOnLaunch']:
            print("WARN: Instance is launched in a public subnet, but the subnet has"
                  " `MapPublicIpOnLaunch` set to `false`. In order for Elastio workers"
                  " to be able to access internet, `MapPublicIpOnLaunch` must be set to `true`.")
        else:
            print("Instance is running in a public subnet; exiting")
        return

    all_traffic_route = get_all_traffic_route(instance_route_table)

    if all_traffic_route is not None:
        print(f"Route table already has a route for 0.0.0.0/0; exiting. {all_traffic_route}")
        return

    nat_subnet_id = choose_subnet_for_nat(
        subnets,
        public_subnets_ids,
        instance_subnet_id,
        instance_vpc_id,
    )

    if nat_subnet_id is None:
        print("Unable to find a public subnet for NAT in the same availability zone; exiting")
        return

    print(f"choosing {nat_subnet_id}")

    stack_name = f"{NAT_CFN_PREFIX}{nat_subnet_id}"

    if not is_stack_deployed(stack_name):
        print(f"No existing stack '{stack_name}' found, deploying new stack")
        deploy_nat_stack(stack_name, nat_subnet_id, instance_route_table_id)
    else:
        print(f"Stack {stack_name} already exists or is in progress; nothing more to do.")


def get_stack_status(stack_name):
    try:
        stacks = request(
            cfn,
            'describe_stacks',
            'Stacks',
            StackName=stack_name,
        )
        return stacks[0]['StackStatus']
    except cfn.exceptions.ClientError as e:
        if 'does not exist' in str(e):
            print(f"Stack with a name {stack_name} does not exist.")
        else:
            print(f"Error describing stack {stack_name}: {e}")
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
            ]
        )
        print(f"Stack creation initiated for {stack_name}: {response}")
    except cfn.exceptions.AlreadyExistsException:
        print(f"Stack {stack_name} already exists")


def choose_subnet_for_nat(subnets, public_subnets_ids, instance_subnet_id, vpc_id):
    nat_deployments = list(get_nat_deployments(subnets))
    print("nat_deployments:", nat_deployments)

    instance_az = subnets[instance_subnet_id]['AvailabilityZone']

    for nat_deployment in nat_deployments:
        if nat_deployment.vpc_id == vpc_id and nat_deployment.az == instance_az:
            print(f"Found already existing NAT deployment: {nat_deployment}")
            return nat_deployment.subnet_id

    print(f"No existing deployments found for {vpc_id}/{instance_az}")

    for subnet_id in sorted(list(public_subnets_ids)):
        if subnets[subnet_id]['AvailabilityZone'] != instance_az:
            continue
        return subnet_id
    return None


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


def cleanup_nat(current_instance_id, event_time):
    subnets = {sn['SubnetId']: sn for sn in request(
        ec2,
        'describe_subnets',
        'Subnets',
    )}
    print("subnets:", subnets)

    nat_deployments = list(get_nat_deployments(subnets))
    print("nat_deployments:", nat_deployments)

    if len(nat_deployments) == 0:
        print("No NAT Gateway deployments found; nothing to do.")
        return

    elastio_instances = {instance['InstanceId']: instance for instance in request(
        ec2,
        'describe_instances',
        'Reservations[].Instances[]',
        Filters=[{'Name': 'tag:elastio:resource', 'Values': ['true']}],
    )}
    print("elastio_instances:", elastio_instances)

    try:
        pending_cleanups = get_pending_cleanups(
            subnets,
            elastio_instances,
            current_instance_id,
            event_time,
        )
        print("pending_cleanups:", pending_cleanups)
    except Exception as e:
        print("Failed to list pending cleanups; assuming there are none", e)
        pending_cleanups = {}

    def instance_az(inst):
        return subnets.get(inst['SubnetId'], {}).get('AvailabilityZone')

    active_statuses = ('pending', 'running', 'stopping')

    for nat_deployment in nat_deployments:
        nat_vpc_id = nat_deployment.vpc_id
        nat_az = nat_deployment.az

        active_instances = (
            instance for instance in elastio_instances.values()

            # VpcId is not always present in the instance object.
            # It isn't present in case if the instance is in shutting-down state,
            # for example (seen during testing). Maybe there are some other cases
            # where VpcId isn't present, so we gracefully default to `None`.
            if (instance['State']['Name'] in active_statuses
                and
                instance.get('VpcId', None) == nat_vpc_id
                and
                instance_az(instance) == nat_az)
        )

        if next(active_instances, None) is not None:
            statuses = '/'.join(active_statuses)
            print(f"Found {statuses} elastio instances in {nat_vpc_id}/{nat_az};"
                  f" skipping NAT gateway stack deletion.")
            continue

        print(f"No elastio instances found in {nat_vpc_id}/{nat_az}")

        if pending_cleanups.contains(nat_vpc_id, nat_az):
            print(f"There is a more recent cleanup pending for {nat_vpc_id}/{nat_az}; skipping.")
            continue

        stack_name = f"{NAT_CFN_PREFIX}{nat_deployment.subnet_id}"

        if is_stack_needs_to_be_deleted(stack_name):
            print(f"Initiating deletion of NAT gateway stack '{stack_name}' for {nat_vpc_id}/{nat_az}.")
            delete_nat_gateway_stack(stack_name)


def get_pending_cleanups(subnets, elastio_instances, current_instance_id, event_time):
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

    pending_cleanups = PendingCleanups()

    for execution_arn in execution_arns:
        execution = sfn.describe_execution(
            executionArn=execution_arn,
        )
        exec_input = json.loads(execution['input'])
        instance_id = exec_input['detail']['instance-id']
        exec_time = datetime.fromisoformat(exec_input['time'])

        # skip the execution that invoked the currently running lambda
        if instance_id == current_instance_id:
            continue

        # if the instance event of the execution is older than one we
        # are currently handling, then we should do the cleanup, so
        # we don't add the vpc/az to the set
        if event_time is not None and exec_time < event_time:
            continue

        instance = elastio_instances.get(instance_id)
        if instance is None:
            continue

        subnet = subnets.get(instance['SubnetId'])
        if subnet is None:
            continue

        vpc_id = subnet['VpcId']
        az = subnet['AvailabilityZone']
        pending_cleanups.add(vpc_id, az)

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
        print(f"Stack deletion initiated for {stack_name}:", response)
    except cfn.exceptions.ClientError as e:
        if 'does not exist' in str(e):
            print(f"Stack {stack_name} does not exist anymore")
        else:
            print(f"Failed to delete stack {stack_name}", e)


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
        yield NatDeployment(stack_id, vpc_id, subnet_id, az)


@dataclass
class NatDeployment:
    stack_id: str
    vpc_id: str
    subnet_id: str
    az: str


class PendingCleanups:
    def __init__(self):
        self.vpc_id_to_zones = {}

    def __str__(self):
        return str(self.vpc_id_to_zones)

    def add(self, vpc_id, availability_zone):
        zones = self.vpc_id_to_zones.pop(vpc_id, set())
        zones.add(availability_zone)
        self.vpc_id_to_zones[vpc_id] = zones

    def contains(self, vpc_id, availability_zone):
        zones = self.vpc_id_to_zones.get(vpc_id, set())
        return availability_zone in zones
