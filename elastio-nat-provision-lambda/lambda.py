import boto3
import botocore
import json
import os
import time

cfn = boto3.client('cloudformation')
ec2 = boto3.client('ec2')
sfn = boto3.client('stepfunctions')

LAMBDA_STACK_ID = os.environ['LAMBDA_STACK_ID']
NAT_CFN_PREFIX = os.environ['NAT_CFN_PREFIX']
NAT_CFN_TEMPLATE_URL = os.environ['NAT_CFN_TEMPLATE_URL']


def lambda_handler(event, _context):
    print(f"boto3 version: {boto3.__version__}")
    print(f"botocore version: {botocore.__version__}")
    print("event:", event)

    if bool(event.get('elastio_scheduled_cleanup')):
        cleanup_nat(None)
    else:
        instance_id = event['detail']['instance-id']
        instance_state = event['detail']['state']

        if instance_state == 'pending':
            ensure_nat(instance_id)
        elif instance_state in ('stopped', 'terminated'):
            cleanup_nat(instance_id)


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

    if not any(tag['Key'] == 'elastio:resource' and tag['Value'] == 'true' for tag in instance_tags):
        print(f"No matching elastio:resource tag found on instance {instance_id}; no action taken.")
        return

    subnets = {sn['SubnetId']: sn for sn in request(
        ec2,
        'describe_subnets',
        'Subnets',
        Filters=[{'Name': 'vpc-id', 'Values': [instance_vpc_id]}],
    )}

    route_tables = {rt['RouteTableId']: rt for rt in request(
        ec2,
        'describe_route_tables',
        'RouteTables',
        Filters=[{'Name': 'vpc-id', 'Values': [instance_vpc_id]}],
    )}

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
    instance_route_table_id = subnet_to_route_table[instance_subnet_id]
    instance_route_table = route_tables[instance_route_table_id]

    if not public_subnets_ids:
        print(f"No public subnets found in {instance_vpc_id}; exiting")
        return

    if instance_subnet_id in public_subnets_ids:
        print("Instance is running in a public subnet; exiting")
        return

    all_traffic_route = get_all_traffic_route(instance_route_table)

    if all_traffic_route is not None:
        print(f"Route table already has a route for 0.0.0.0/0; exiting. {all_traffic_route}")
        return

    print("subnets:", subnets)
    print("public_subnets_ids:", public_subnets_ids)
    print("instance_subnet_id:", instance_subnet_id)

    nat_subnet_id = choose_subnet_for_nat(subnets, public_subnets_ids, instance_subnet_id)

    if nat_subnet_id is None:
        print("Unable to find a subnet in the same availability zone; exiting")
        return

    stack_name = f"{NAT_CFN_PREFIX}{instance_vpc_id}"

    if not is_stack_deployed(stack_name):
        print(f"No existing stack found for {instance_vpc_id}, deploying new NAT gateway stack '{stack_name}'.")
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
    response = cfn.create_stack(
        StackName=stack_name,
        TemplateURL=NAT_CFN_TEMPLATE_URL,
        OnFailure='DELETE',
        Parameters=[
            {
                'ParameterKey': 'SubnetId',
                'ParameterValue': subnet_id
            },
            {
                'ParameterKey': 'RouteTableId',
                'ParameterValue': route_table_id
            },
        ],
    )
    print(f"Stack creation initiated for {stack_name}: {response}")


def choose_subnet_for_nat(subnets, public_subnets_ids, instance_subnet_id):
    instance_az = subnets[instance_subnet_id]['AvailabilityZone']

    for subnet_id, subnet in subnets.items():
        if subnet_id not in public_subnets_ids:
            continue
        if subnet['AvailabilityZone'] != instance_az:
            continue
        return subnet_id


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


def cleanup_nat(current_instance_id):
    elastio_instances = {instance['InstanceId']: instance for instance in request(
        ec2,
        'describe_instances',
        'Reservations[].Instances[]',
        Filters=[{'Name': 'tag:elastio:resource', 'Values': ['true']}],
    )}

    active_instances_count = sum(
        1 for instance in elastio_instances.values()
        if instance['State']['Name'] in ('pending', 'running', 'stopping', 'shutting-down')
    )

    if active_instances_count > 0:
        print(f"Found {active_instances_count} running/pending/stopping elastio instances;"
              " skipping NAT gateway stack deletion.")
        return

    print("No elastio instances found.")

    try:
        pending_cleanups = pending_cleanups_vpc_ids(elastio_instances, current_instance_id)
    except Exception as e:
        print("Failed to list pending cleanups; assuming there are none", e)
        pending_cleanups = set()

    vpcs = request(
        ec2,
        'describe_vpcs',
        'Vpcs'
    )

    for vpc in vpcs:
        vpc_id = vpc['VpcId']
        stack_name = f"{NAT_CFN_PREFIX}{vpc_id}"

        if vpc_id in pending_cleanups:
            print(f"There is a more recent cleanup pending for stack {stack_name}; skipping.")
            continue

        if is_stack_needs_to_be_deleted(stack_name):
            print(f"Initiating deletion of NAT gateway stack '{stack_name}' for {vpc_id}.")
            delete_nat_gateway_stack(stack_name)


def pending_cleanups_vpc_ids(elastio_instances, current_instance_id):
    """
    Returns VPC ids for which there are pending cleanup tasks in the state machine,
    currently waiting for the quiescent period.
    """
    state_machine_arn = request(
        cfn,
        'describe_stacks',
        "Stacks[].Outputs[?OutputKey=='natGatewayCleanupStateMachineArn'][].OutputValue",
        StackName=LAMBDA_STACK_ID,
    )[0]

    execution_arns = request(
        sfn,
        'list_executions',
        'executions[].executionArn',
        stateMachineArn=state_machine_arn,
        statusFilter='RUNNING',
    )

    vpc_ids = set()

    for execution_arn in execution_arns:
        execution = sfn.describe_execution(
            executionArn=execution_arn,
        )
        exec_input = json.loads(execution['input'])
        instance_id = exec_input['detail']['instance-id']

        # skip execution that invoked currently running lambda
        if instance_id == current_instance_id:
            continue

        if instance_id in elastio_instances:
            vpc_id = elastio_instances[instance_id]['VpcId']
            vpc_ids.add(vpc_id)

    print("pending vpc_ids:", vpc_ids)
    return vpc_ids


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
    response = cfn.delete_stack(StackName=stack_name)
    print(f"Stack deletion initiated for {stack_name}:", response)
