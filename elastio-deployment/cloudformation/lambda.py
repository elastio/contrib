from urllib.request import Request, urlopen
import os
import json
from urllib.error import HTTPError


def lambda_handler(event, context):
    def send_cfn_response(status, reason=None):
        print(f"Sending response to CloudFormation: {status} - {reason}")

        response_body = {
            "Status": status,
            "Reason": reason or "See CloudWatch logs",
            "PhysicalResourceId": context.log_stream_name,
            "StackId": event["StackId"],
            "RequestId": event["RequestId"],
            "LogicalResourceId": event["LogicalResourceId"],
        }

        req = Request(
            event["ResponseURL"],
            data=json.dumps(response_body).encode(),
            headers={"Content-Type": "application/json"},
            method="PUT",
        )

        with urlopen(req) as response:
            print(response.read().decode())

    try:
        if event["RequestType"] == "Create" or event["RequestType"] == "Update":
            run()
        send_cfn_response("SUCCESS")
    except HTTPError as e:
        send_cfn_response("FAILED", f"{e}: {e.read().decode()}")
    except Exception as e:
        send_cfn_response("FAILED", str(e))
        raise


def run():
    elastio_pat = os.environ["ELASTIO_PAT"]
    elastio_tenant = os.environ["ELASTIO_TENANT"]
    elastio_endpoint = f"https://{elastio_tenant}/public-api/v1"

    subnet_ids = os.environ.get("ELASTIO_SUBNET_IDS")

    request_body = {
        "region": os.environ["AWS_REGION"],
        "account_id": os.environ["ELASTIO_AWS_ACCOUNT_ID"],
        #
        # None `vpc_id/subnet_ids` means we'll created a new Elastio-managed VPC
        "vpc_id": os.environ.get("ELASTIO_VPC_ID") or "",
        "subnet_ids": subnet_ids.split(",") if subnet_ids else [],
    }

    req = Request(
        f"{elastio_endpoint}/deploy-cloud-connector",
    )
    req.add_header("Authorization", f"Bearer {elastio_pat}")
    req.add_header("User-Agent", "urllib")
    req.add_header("Content-Type", "application/json; charset=utf-8")

    data = json.dumps(request_body).encode()

    for attempt in range(5):
        try:
            print(f"Sending request to Elastio: POST {req.full_url}")
            print(json.dumps(request_body))
            with urlopen(req, data) as response:
                print(response.read().decode())
            return
        except HTTPError as e:
            print(f"HTTPError: {e.read().decode()}")

            if attempt == 4:  # Last attempt
                raise
