import time

import boto3


def _is(s):
    return True if "elastio" in s.lower() else False


def _confirm():
    r = input("Delete resource?").lower
    if r == "y" or r == "yes":
        return True


def scan_ec2(d, r):
    c = boto3.client("ec2", region_name=r)
    count = 0
    res = c.describe_launch_templates()
    for lt in res["LaunchTemplates"]:
        if _is(lt["LaunchTemplateName"]):
            count += 1
            if d and _confirm():
                c.delete_launch_template(LaunchTemplateName=lt["LaunchTemplateName"])
                print("Deleted", lt["LaunchTemplateName"])
    print(f"{count} EC2 Launch Templates Discovered")


def scan_cloudwatch(d, r):
    count = 0
    c = boto3.client("cloudwatch", region_name=r)
    res = c.describe_alarms()
    for alarm in res["CompositeAlarms"]:
        count += 1
        if _is(alarm["AlarmName"]):
            count += 1
            if d:
                c.delete_alarms(AlarmNames=[alarm["AlarmName"]])
    for alarm in res["MetricAlarms"]:
        if _is(alarm["AlarmName"]):
            count += 1
            if d and _confirm():
                c.delete_alarms(AlarmNames=[alarm["AlarmName"]])
    print(f"{count} Cloudwatch Alarms Detected")


def scan_event_bridge(d, r):
    count = 0
    c = boto3.client("events", region_name=r)
    res = c.list_rules()
    for re in res["Rules"]:
        if _is(re["Name"]):
            count += 1
            targets = c.list_targets_by_rule(Rule=re["Name"])
            if d and _confirm():
                for t in targets["Targets"]:
                    c.remove_targets(Rule=re["Name"], Ids=[t["Id"]])
                    time.sleep(1)
                c.delete_rule(Name=re["Name"])
    print(f"{count} Cloudwatch Events Detected")


def scan_ssm(d, r):
    count = 0
    c = boto3.client("ssm", region_name=r)
    res = c.describe_parameters(
        ParameterFilters=[
            {"Key": "Name", "Option": "BeginsWith", "Values": ["/elastio"]}
        ]
    )
    for p in res["Parameters"]:
        if _is(p["Name"]):
            count += 1
            if d and _confirm():
                c.delete_parameter(Name=p["Name"])
    print(f"{count} SSM Parameters Detected")


def scan_autoscaling_plans(d, r):
    count = 0
    c = boto3.client("autoscaling-plans", region_name=r)
    a = c.describe_scaling_plans()
    for sp in a["ScalingPlans"]:
        for tags in sp["ApplicationSource"]["TagFilters"]:
            for val in tags["Values"]:
                if _is(val):
                    count += 1
                    if d and _confirm():
                        c.delete_scaling_plan(
                            ScalingPlanName=sp["ScalingPlanName"], ScalingPlanVersion=1
                        )
    print(f"{count} AutoScaling Plans Detected")


def scan_lambda(d, r):
    count = 0
    c = boto3.client("lambda", region_name=r)
    lf = c.list_functions()
    for f in lf["Functions"]:
        if _is(f["FunctionName"]):
            count += 1
            if d and _confirm():
                c.delete_function(FunctionName=f["FunctionName"])
    print(f"{count} Lambda Functions Detected")


def scan_cloudformation(d, r):
    count = 0
    c = boto3.client("cloudformation", region_name=r)
    res = c.list_stacks()
    for s in res["StackSummaries"]:
        if _is(s["StackName"]) and s["StackStatus"] != "DELETE_COMPLETE":
            count += 1
            if d and s["StackStatus"] and _confirm():
                c.delete_stack(StackName=s["StackName"])
    print(f"{count} Cloudformation Stacks Detected")


def scan_sns(d, r):
    count = 0
    c = boto3.client("sns", region_name=r)
    res = c.list_topics()
    for t in res["Topics"]:
        if _is(t["TopicArn"]):
            count += 1
            if d and _confirm():
                c.delete_topic(TopicArn=t["TopicArn"])
    print(f"{count} SNS Topics Detected")


def scan_sqs(d, r):
    count = 0
    c = boto3.client("sqs", region_name=r)
    res = c.list_queues()

    if "QueueUrls" in res:

        for q in res["QueueUrls"]:
            if _is(q):
                count += 1
                if d and _confirm():
                    c.delete_queue(QueueUrl=q)

    print(f"{count} SQS Queues Detected")


def scan_ecs(d, r):
    count = 0
    c = boto3.client("ecs", region_name=r)
    res = c.list_clusters()
    for arn in res["clusterArns"]:
        if _is(arn):
            count += 1
            if d and _confirm():
                print("No Destructors Found for ECS. Please delete manually and rerun")
    print(f"{count} ECS Clusters Detected")


def scan_kms(d, r):
    count = 0
    c = boto3.client("kms", region_name=r)
    res = c.list_keys()
    for k in res["Keys"]:
        ka = c.list_aliases(KeyId=k["KeyId"])
        kd = c.describe_key(KeyId=k["KeyId"])
        keyState = kd["KeyMetadata"]["KeyState"]
        for a in ka["Aliases"]:
            if _is(a["AliasName"]) and keyState != "PendingDeletion":
                count += 1
                if d and _confirm():
                    c.disable_key(KeyId=k["KeyId"])
                    c.schedule_key_deletion(KeyId=k["KeyId"], PendingWindowInDays=7)
    print(f"{count} KMS Keys Detected")


def scan_batch(d, r):
    count = 0
    c = boto3.client("batch", region_name=r)
    res = c.describe_job_queues()
    for j in res["jobQueues"]:
        if _is(j["jobQueueName"]):
            count += 1
            jq = j["jobQueueArn"]
            if d and _confirm():
                c.update_job_queue(jobQueue=jq, state="DISABLED")
                time.sleep(10)
                c.delete_job_queue(jobQueue=j["jobQueueArn"])
    print(f"{count} Batch Job Queues Detected")

    count = 0
    res = c.describe_job_definitions()
    for j in res["jobDefinitions"]:
        if _is(j["jobDefinitionName"]) and j["status"] != "INACTIVE":
            count += 1
            jd = j["jobDefinitionArn"]
            if d and _confirm():
                c.deregister_job_definition(jobDefinition=jd)
    print(f"{count} Batch Jobs Definitions Detected")

    count = 0
    res = c.describe_compute_environments()
    for j in res["computeEnvironments"]:
        count += 1
        if _is(j["computeEnvironmentName"]):
            if d and _confirm():
                c.update_compute_environment(
                    computeEnvironment=j["computeEnvironmentArn"], state="DISABLED"
                )
                time.sleep(20)
                c.delete_compute_environment(
                    computeEnvironment=j["computeEnvironmentArn"]
                )
    print(f"{count} Batch Compute Environments Detected")


def scan(event, context):
    scan_ec2(event.destroy, event.region)
    scan_cloudwatch(event.destroy, event.region)
    scan_event_bridge(event.destroy, event.region)
    scan_lambda(event.destroy, event.region)
    scan_cloudformation(event.destroy, event.region)
    scan_sns(event.destroy, event.region)
    scan_sqs(event.destroy, event.region)
    scan_ssm(event.destroy, event.region)
    scan_ecs(event.destroy, event.region)
    scan_kms(event.destroy, event.region)
    scan_batch(event.destroy, event.region)
