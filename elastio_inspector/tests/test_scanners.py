from moto import (
    mock_batch,
    mock_cloudformation,
    mock_cloudwatch,
    mock_ec2,
    mock_ecs,
    mock_events,
    mock_kms,
    mock_lambda,
    mock_sns,
    mock_sqs,
    mock_ssm,
)

from elastio_inspector.handler import (
    scan_batch,
    scan_cloudformation,
    scan_cloudwatch,
    scan_ec2,
    scan_ecs,
    scan_event_bridge,
    scan_kms,
    scan_lambda,
    scan_sns,
    scan_sqs,
    scan_ssm,
)


@mock_ec2
def test_scan_ec2():
    scan_ec2(False, "us-east-1")


@mock_cloudwatch
def test_scan_cloudwatch():
    scan_cloudwatch(False, "us-east-1")


@mock_events
def test_scan_event_bridge():
    scan_event_bridge(False, "us-east-1")


@mock_ssm
def test_scan_ssm():
    scan_ssm(False, "us-east-1")


@mock_ecs
def test_scan_ecs():
    scan_ecs(False, "us-east-1")


@mock_sns
def test_scan_sns():
    scan_sns(False, "us-east-1")


@mock_sqs
def test_scan_sqs():
    scan_sqs(False, "us-east-1")


@mock_kms
def test_scan_kms():
    scan_kms(False, "us-east-1")


@mock_batch
def test_scan_batch():
    scan_batch(False, "us-east-1")


@mock_lambda
def test_scan_lambda():
    scan_lambda(False, "us-east-1")


@mock_cloudformation
def test_scan_cloudformation():
    scan_cloudformation(False, "us-east-1")
