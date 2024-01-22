from datetime import datetime
from json import JSONEncoder
import boto3
import json
import time
import random

PRODUCT_NAME = "DeployElastioCfn"
ROLE_NAME = "ElastioCfnRole"  # Role to assume in the target account
MAX_RETRIES = 10
RETRY_DELAY = 30  # seconds
TAGS = [{'Key': 'elastio:resource', 'Value': 'true'}]


class DateTimeEncoder(JSONEncoder):

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return JSONEncoder.default(self, obj)


def assume_role_with_retry(account_id,
                           role_name,
                           max_retries=MAX_RETRIES,
                           retry_delay=RETRY_DELAY):

    sts_client = boto3.client('sts')
    role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"

    for attempt in range(max_retries):
        try:
            assumed_role = sts_client.assume_role(
                RoleArn=role_arn, RoleSessionName="AssumeRoleSession")

            return assumed_role['Credentials']
        except Exception as e:
            print(f"Attempt {attempt + 1} to assume role failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                raise


def get_product_info(credentials, product_name):
    servicecatalog = boto3.client(
        'servicecatalog',
        aws_access_key_id=credentials['AccessKeyId'],
        aws_secret_access_key=credentials['SecretAccessKey'],
        aws_session_token=credentials['SessionToken'])

    # Find the product by name
    response = servicecatalog.search_products(
        Filters={'FullTextSearch': [product_name]})
    print("Search Products Response:",
          json.dumps(response, indent=2, cls=DateTimeEncoder))
    products = response.get('ProductViewSummaries', [])
    product_id = next((item['ProductId']
                       for item in products if item['Name'] == product_name),
                      None)

    if not product_id:
        raise ValueError(f"Product '{product_name}' not found")

    # Get the latest provisioning artifact (version) for the product
    response = servicecatalog.describe_product(Id=product_id)
    print("Describe Product Response:",
          json.dumps(response, indent=2, cls=DateTimeEncoder))
    provisioning_artifacts = response.get('ProvisioningArtifacts', [])

    if not provisioning_artifacts:
        raise ValueError(
            f"No provisioning artifacts found for product '{product_name}'")

    latest_artifact = max(provisioning_artifacts,
                          key=lambda x: x['CreatedTime'])
    provisioning_artifact_id = latest_artifact['Id']

    return product_id, provisioning_artifact_id


def launch_product(credentials, product_id, provisioning_artifact_id,
                   product_name):
    servicecatalog = boto3.client(
        'servicecatalog',
        aws_access_key_id=credentials['AccessKeyId'],
        aws_secret_access_key=credentials['SecretAccessKey'],
        aws_session_token=credentials['SessionToken'])

    product_name = f"{product_name}-{random.randint(10000000, 99999999)}"
    response = servicecatalog.provision_product(
        ProductId=product_id,
        ProvisioningArtifactId=provisioning_artifact_id,
        ProvisionedProductName=product_name,
        Tags=TAGS)

    # Convert datetime objects to strings in the response
    response['RecordDetail']['CreatedTime'] = str(
        response['RecordDetail']['CreatedTime'])
    response['RecordDetail']['UpdatedTime'] = str(
        response['RecordDetail']['UpdatedTime'])

    return response


def lambda_handler(event, context):
    try:
        # Try to get the account ID from CreateManagedAccount event
        new_account_id = event.get('detail',
                                   {}).get('serviceEventDetails', {}).get(
                                       'createManagedAccountStatus',
                                       {}).get('account', {}).get('accountId')

        # Fallback to the account ID from CreateAccountResult event
        if not new_account_id:
            new_account_id = event.get('detail',
                                       {}).get('serviceEventDetails',
                                               {}).get('createAccountStatus',
                                                       {}).get('accountId')

        if not new_account_id:
            raise ValueError("New account ID not found in the event")

        credentials = assume_role_with_retry(new_account_id, ROLE_NAME)

        for attempt in range(MAX_RETRIES):
            try:
                product_id, provisioning_artifact_id = get_product_info(
                    credentials, PRODUCT_NAME)
                response = launch_product(credentials, product_id,
                                          provisioning_artifact_id,
                                          PRODUCT_NAME)
                print("Product launch response:",
                      json.dumps(response, indent=2, cls=DateTimeEncoder))

                return {"status": "success", "response": response}
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                else:
                    raise e
    except Exception as e:
        print(f"Error processing event: {e}")
        return {"status": "error", "message": str(e)}

    return {"status": "success"}
