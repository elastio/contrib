import boto3
import subprocess
import datetime
import json

from failed_ecs_handler_config import CLUSTER_NAME

cluster_name = CLUSTER_NAME
expired_time = 20 # minutes
ecs_client = boto3.client('ecs')

# Getting list of stopped task from cluster.
list_task_response = ecs_client.list_tasks(
    cluster=cluster_name,
    desiredStatus='STOPPED',
    launchType='EC2'
)
# Getting recovery point list from Elastio CLI.
res = subprocess.run(
        ['elastio', 'rp', 'list', '--output-format', 'json', '--type', 'ec2'],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
rps = [json.loads(rp) for rp in res.stdout.splitlines()]
# Getting arn previously backed up ecs tasks.
rps_tasks_arn = (rp['tags']['taskARN'] for rp in rps[0] if 'taskARN' in rp['tags'].keys())
tasks = list_task_response['taskArns']
if tasks != []:
    for t in tasks:
        # Getting task description
        t_desc = ecs_client.describe_tasks(
            cluster=cluster_name,
            tasks=[t, ]
        )
        task_arn = t_desc['tasks'][0]['taskArn']
        if task_arn not in rps_tasks_arn:
            print("New task ARN: {}.".format(task_arn))
            task_stopped_at = t_desc['tasks'][0]['pullStoppedAt']
            delta_time = task_stopped_at + datetime.timedelta(minutes=expired_time)
            # If the task stopped more than 20 minutes ago, the instance is most likely already terminated.
            if delta_time > datetime.datetime.now(datetime.timezone.utc):
                container_arn = t_desc['tasks'][0]['containerInstanceArn']
                # Getting container description by task
                container_instance_desc = ecs_client.describe_container_instances(
                    cluster=cluster_name,
                    containerInstances=(container_arn, )
                )
                for container in container_instance_desc['containerInstances']:
                    subprocess.run(
                            ['elastio', 'ec2', 'backup', '--instance-id', container['ec2InstanceId'],'--vault', 'defl', '--tag', 'taskARN={task_arn}'.format(task_arn=task_arn)]
                        )
                    print(f"Elastio start job to backup {container['ec2InstanceId']} instance.")
            else:
                print(f"The time to backup task {task_arn} has expired.")
else:
    print("You don't have any stopped tasks.")
