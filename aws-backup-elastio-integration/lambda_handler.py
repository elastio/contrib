# pylint: disable = C0103, R0902, C0301, C0330, C0303, C0326, W1202
"""
Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

Permission is hereby granted, free of charge, to any person obtaining a copy of this
software and associated documentation files (the "Software"), to deal in the Software
without restriction, including without limitation the rights to use, copy, modify,
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import logging
import traceback
import json
import uuid
import boto3
from botocore.exceptions import ClientError

MAX_SEC_HUB_MALWARE_FINDINGS = 5
logger = logging.getLogger()
logger.setLevel(logging.INFO)
sechub_client = boto3.client('securityhub')

def handle_aws_backup_event(event):
    """
    This method is responsible for processing the AWS Backup Events to initiate 
    an elastio scan
    """    
    try:
        #Get the tags that this lambda will look for in an RP before sending to elastio
        ENABLE_ELASTIO_SCAN_TAG_LIST = os.environ.get('ElastioScanTag') 
        if not ENABLE_ELASTIO_SCAN_TAG_LIST:
            logger.info(f'NO Tags defined to filter inside an RP. Skipping processing')   
            return
        
        ENABLE_ELASTIO_SCAN_TAG_LIST = ENABLE_ELASTIO_SCAN_TAG_LIST.split(",")

        event_detail = event.get('detail')
        job_event_state = event_detail.get('state')
        backup_vault_name = event_detail.get('backupVaultName')
        resources = event.get('resources')
        recovery_point_arn = None
        for resource in resources:
            if not ':backup-vault:' in resource:
                recovery_point_arn = resource
        if not job_event_state:
            # Hack
            job_event_state = event_detail.get('status')
        if job_event_state == 'COMPLETED':
            backup_client = boto3.client('backup')
            response = backup_client.list_tags(ResourceArn=recovery_point_arn)
            tag_list = response.get('Tags')
            enable_elastio_scan = any(item in tag_list for item in ENABLE_ELASTIO_SCAN_TAG_LIST)

            #Existence of Scan enable or the Lambda trigger tag
            if (enable_elastio_scan):
                elastio_status_eb = os.environ.get('ElastioStatusEB') 
                if not elastio_status_eb:
                    logger.info(f'ElastioStatusEB env variable NOT defined. Defaulting to elastio-scan-results.')
                    elastio_status_eb = 'elastio-scan-results'
                
                elastio_lambda_arn = os.environ.get('ElastioImportLambdaARN') 
                if not elastio_lambda_arn:
                    if not LAMBDA_TRIGGER_TAG:
                       elastio_lambda_arn = tag_list[LAMBDA_TRIGGER_TAG].lower()
                    else:
                        raise Exception('ElastioImportLambdaARN is missing!') 
                
                #invoke the lambda
                input_params = {
                                "aws_backup_vault": backup_vault_name,
                                "aws_backup_rp_arn": recovery_point_arn,
                                "iscan": {
                                    "ransomware": True,
                                    "malware": True,
                                    "event_bridge_bus": elastio_status_eb
                                }
                                }

                # Let the customer control whether we do a scan-only, ingest, or ingest-and-scan 
                # of this RP.  If no `elastio:action` tag is specified, we'll let the Elastio
                # integration Lambda decide what the default behavior should be.    
                #
                # the odd for loop is needed because we want this tag to be case-insensitive to maximum
                # customer convenience.
                elastio_action = None
                for tag in tag_list.keys():  # Iterate over the keys in tag_list
                    if tag.lower() == 'elastio:action':  # Case-insensitive comparison
                        elastio_action = tag_list[tag].lower()  # Convert the value to lower case
                        break  # Exit the loop once the tag is found
                
                if elastio_action:
                    if elastio_action not in ["scan", "ingest", "ingest-and-scan"]:
                        logger.warning(f'Invalid action "{elastio_action}" specified for RP {recovery_point_arn}. Defaulting to "ingest-and-scan".')
                        elastio_action = "ingest-and-scan"
                    
                    input_params['action'] = elastio_action
                    logger.info(f'Action specified for RP {recovery_point_arn} is {elastio_action}')
                
                logger.info(f'invoking {elastio_lambda_arn} with {input_params}')
                try:
                    boto3.client('lambda').invoke(
                        FunctionName=elastio_lambda_arn,
                        InvocationType='Event',
                        Payload=json.dumps(input_params)
                    )
                except (ClientError, Exception):  # pylint: disable = W0703
                    var = traceback.format_exc()
                    logger.error(f"Error {var} processing invoke for elastio iscan lambda")                         
    except Exception:
        var = traceback.format_exc()
        logger.error(f"Error {var} in handle_aws_backup_event")                   
            
def save_event_data_to_s3(s3_log_bucket,json_content):
    """
    This method is responsible for writing the json_content to the s3_log_bucket
    """
    try:
        job_id = json_content.get('job_id') 
        s3_log_location = 'elastio-scan-results/' + job_id + '.json'        
        logger.info(f"Persisting event data to : {s3_log_bucket} at {s3_log_location}")
        s3_client = boto3.client('s3')
        s3_client.put_object(Body=json.dumps(json_content,
                                           default=str, separators=(',', ':')),
                           Bucket=s3_log_bucket,
                           Key=s3_log_location, ACL='bucket-owner-full-control',
                           Tagging='Source=ElastioResults')
    except (ClientError, Exception):
        var = traceback.format_exc()
        logger.error(f"Error {var} processing save_event_data_to_s3") 
      
def process_ransomware_details(account_id,product_arn,generator_id,scan_timestamp,aws_asset_id,aws_backup_rp_arn,elastio_rp_id,ransomware_details):
    """
    This is the function responsible to create ransomware findings based on ransomware_details
    """      
    try:
        logger.info(f'Starting process_ransomware_details')
        title = 'Ransomware scan results'
        ransomware_report = ransomware_details['report']
        if ransomware_report:
            ransomware_encrypted_files = ransomware_report.get('encrypted_files')
            if ransomware_encrypted_files:
                ransomware_state = 'OBSERVED'
                for ransomware_encrypted_file in ransomware_encrypted_files:
                    parent_directory = ransomware_encrypted_file.get('parent_directory')
                    filename = ransomware_encrypted_file.get('filename')
                    file_path = f'{parent_directory}/{filename}'
                    suspected_ransomware = ransomware_encrypted_file.get('suspected_ransomware')
                    suspected_ransomware_names = [suspected_ransomware_item['name'] for suspected_ransomware_item in suspected_ransomware]
                    
                    # Convert the list of names into a comma-separated string
                    suspected_ransomware_names = ', '.join(suspected_ransomware_names)
                    scan_result_type = 'RANSOMWARE'
                    
                    ransomware_obj = { 
                                      'Name': suspected_ransomware_names,
                                      'Path': file_path,
                                      'State': ransomware_state,
                                      'Type': scan_result_type
                                  }
                    import_security_hub_findings(account_id,product_arn,generator_id,scan_timestamp,title,aws_asset_id,aws_backup_rp_arn,elastio_rp_id,ransomware_obj)
    except (ClientError, Exception):
        var = traceback.format_exc()
        logger.error(f"Error {var} processing process_ransomware_details")
      
          
def process_malware_details(account_id,product_arn,generator_id,scan_timestamp,aws_asset_id,aws_backup_rp_arn,elastio_rp_id,malware_details):
    """
    This is the function responsible to create malware findings based on malware_details
    """        
    try:
        logger.info(f'Starting process_malware_details')
        title = 'Malware scan results'
        malware_report = malware_details['report']
        if malware_report:
            malware_suspicious_files = malware_report.get('suspicious_files')
            if malware_suspicious_files:
                malware_state = 'OBSERVED'
                for malware_suspicious_file in malware_suspicious_files:
                    file_path = malware_suspicious_file.get('path')
                    scan_result = malware_suspicious_file.get('scan_result')
                    malware_name = 'EncryptedFile'
                    scan_result_type = 'BLENDED_THREAT' 
                    if isinstance(scan_result, dict):
                        infected_data = scan_result.get('Infected')
                        if infected_data:
                            scan_result_type =  infected_data.get('threat_type')
                            if scan_result_type and scan_result_type == 'Virus':
                                scan_result_type = 'VIRUS'
                            malware_name = infected_data.get('threat_name')
                    malware_obj = { 
                                      'Name': malware_name,
                                      'Path': file_path,
                                      'State': malware_state,
                                      'Type': scan_result_type
                                  }
                    
                    import_security_hub_findings(account_id,product_arn,generator_id,scan_timestamp,title,aws_asset_id,aws_backup_rp_arn,elastio_rp_id,malware_obj)
                    
    except (ClientError, Exception):
        var = traceback.format_exc()
        logger.error(f"Error {var} processing process_malware_details")      
      
def generate_security_hub_findings(event):
    """
    This is the main function that will process the elastio response JSON to create
    SecurityHub findings
    """ 
    try:
        logger.info('Starting generate_security_hub_findings')
        awsRegion = event['region']
        account_id = event['account']
        generator_id = f"{account_id}/elastio.iscan/{event.get('job_id')}"
        product_arn = 'arn:aws:securityhub:' + awsRegion + ':' + account_id + ':product/' + account_id + '/default'    
        event_details = event['detail']
        scan_timestamp = event['time']
        elastio_scan_reports = event_details.get('reports')
        
        for elastio_report in elastio_scan_reports:
            scan_summary = elastio_report.get('summary')
            aws_backup_rp_arn = elastio_report.get('aws_backup_rp_arn')
            aws_asset_id = scan_summary.get('aws_asset_id')

            # When scanning an Elastio RP, this is a string with the RP ID and the Elastio asset ID separated by `:`, eg
            # rp-01hb8zhddexp111v2wf6zqnx6s:elastio:asset:aws-ebs:s:968455818835:us-east-2:vol-09678ed07cb34fb40
            #
            # When performing scan-only on an AWS Backup RP, the format is $aws_rp_arn:$snapshot_id, eg:
            # aws:ec2:us-east-2::snapshot/snap-09205755f3e7984c7:snap-09205755f3e7984c7
            #
            # Since we already know the backup ARN from a dedicated report field, and don't actually care about
            # the individual EBS snapshot that was scanned, we'll ignore the cases where there is no RP ID for the
            # purposes of generating a SecurityHub alert.
            elastio_asset = elastio_report.get('asset')
            
            if elastio_asset.startswith("rp-") and ":" in elastio_asset:
                elastio_rp_id = elastio_asset.split(":", 1)[0]  # split at the first occurrence of ":" and return the first part
            else:
                elastio_rp_id = None

            is_rp_clean = scan_summary.get('clean')
            malware_details = elastio_report.get('malware')
            ransomware_details = elastio_report.get('ransomware')
            summary_details = elastio_report.get('summary')
            if not is_rp_clean:
                process_malware_details(account_id,product_arn,generator_id,scan_timestamp,aws_asset_id,aws_backup_rp_arn,elastio_rp_id, malware_details)
                process_ransomware_details(account_id,product_arn,generator_id,scan_timestamp,aws_asset_id,aws_backup_rp_arn,elastio_rp_id, ransomware_details)
                create_summary_insights(aws_backup_rp_arn,summary_details)
    except (ClientError, Exception):
        var = traceback.format_exc()
        logger.error(f"Error {var} processing generate_security_hub_findings")   
        
def import_security_hub_findings(account_id,product_arn,generator_id,scan_timestamp,title,aws_asset_id,aws_backup_rp_arn,elastio_rp_id,malware_obj):   
    """
    This function is responsible for creating a finding in SecurityHub based on malware_obj
    """        
    try:
        logger.info(f'Starting import_security_hub_findings')
        finding_id = f"{account_id}/{uuid.uuid4()}"
        description = f'Details of {title} for AWS Backup Recovery Point : {aws_backup_rp_arn}'
        sechub_finding = {
                    'SchemaVersion': '2018-10-08', 
                    'Id': finding_id,
                    'ProductArn': product_arn,
                    'GeneratorId': generator_id,
                    'AwsAccountId': account_id,
                    'Types': [ 'Malware and Ransomware Scans' ],
                    'FirstObservedAt': scan_timestamp,
                    'UpdatedAt': scan_timestamp,
                    'CreatedAt': scan_timestamp,
                    'Severity': {
                      'Label': "HIGH"
                    },
                    'Title': title,
                    'Description': description,
                    'ProductName':'Elastio iScan',
                    'CompanyName':'Elastio',
                    'WorkflowState': 'NEW', 
                    'Compliance': {'Status': 'FAILED'},                    
                    'Resources': [
                      {
                        'Id': aws_asset_id,
                        'Type': "VolumeId"
                      },
                      {
                        'Id': aws_backup_rp_arn,
                        'Type': "RecoveryPointId"
                      },
                    ],
                    'Malware': [malware_obj]
                }
        
        # Some customers only look at SecurityHub, they don't have the optional observability
        # component enabled, so for now the only notice they will get of an adverse finding on the AWS Backup RP
        # will be via SecurityHub.  So it's important that we include the Elastio RP ID so they are able to find
        # it in the UI.
        if elastio_rp_id is not None:
            sechub_finding['Resources'].append({
                'Id': elastio_rp_id,  

                # Per the AWS Security Hub Security Finding Format (https://docs.aws.amazon.com/securityhub/latest/userguide/securityhub-findings-format-syntax.html)
                # non-AWS IDs must have type "Other"
                'Type': 'Other'
            })

        logger.info(f'batch_import_findings with finding : {sechub_finding}')
        response = sechub_client.batch_import_findings(Findings=[sechub_finding])
        successCount=response['SuccessCount']
        failedCount=response['FailedCount']
        failedFindings=response['FailedFindings']
        
        logger.info(f'batch_import_findings finished. FailedCount: {failedCount},SuccessCount : {successCount}. FailedFindings: {failedFindings}')
    except (ClientError, Exception):
        var = traceback.format_exc()
        logger.error(f"Error {var} processing import_security_hub_findings") 

def create_summary_insights(awsbackup_rp_id, summary_details):
    """
    This function is responsible to create an insight based on the findings
    created for the awsbackup_rp_id
    """    
    
    try:
        logger.info(f'Starting create_summary_insights with {summary_details}')
        aws_asset_id = summary_details.get('aws_asset_id')
        insight_name = f'Elastio Scan results for resource : {aws_asset_id} using RP : {awsbackup_rp_id}'
        if len(insight_name) > 128:
            insight_name = insight_name[:125] + '...'
        filters = {
            'ResourceId': [{
                'Value': awsbackup_rp_id,
                'Comparison': 'EQUALS'
            }],
            'ResourceType': [{
                'Value': 'RecoveryPointId',
                'Comparison': 'EQUALS'
            }],
            'CompanyName': [{
                'Value': 'elastio.com',
                'Comparison': 'EQUALS'
            }],
            'WorkflowStatus': [{
                'Value': 'NEW',
                'Comparison': 'EQUALS'
            }]
        }    
        
        group_by_attribute = 'ResourceType'     
        logger.info(f'create_insight :{insight_name} with filter : {filters} and group_by_attribute : {group_by_attribute}')
        
        response = sechub_client.create_insight(
            Name=insight_name,
            Filters=filters,
            GroupByAttribute=group_by_attribute
        )
        insight_arn = response['InsightArn']
        logger.info(f'Insight : {insight_arn} created successfully')
        
    except (ClientError, Exception):
        var = traceback.format_exc()
        logger.error(f"Error {var} processing create_summary_insights")    
    
######################################################################
#                        FUNCTIONAL LOGIC                            #
######################################################################

def handler(event, context):
    """
    Main Handler for AWS Backup and Elastio Integration Lambda
    """
    logger.info(f'Processing Event : {event}')
    try:
        if event.get('source') == 'elastio.iscan':
            job_event_type = 'scan_results'
            event['job_type']=job_event_type
            event['job_id']=event.get('id')
            s3_log_bucket = os.environ.get('LogsBucketName') 
            if s3_log_bucket:
                save_event_data_to_s3(s3_log_bucket,event)
            else:
                logger.info('S3 Log Bucket Name Env Parameter LogsBucketName is missing. Skipping logging to S3 Bucket')
                
            generate_security_hub_findings(event)
            
        #Process AWS Backup Job completion event to trigger Elastio Scan
        elif event.get('source') == 'aws.backup':
            handle_aws_backup_event(event)
    except (ClientError, Exception):
        var = traceback.format_exc()
        logger.error(f"Error {var} processing handler")  
        