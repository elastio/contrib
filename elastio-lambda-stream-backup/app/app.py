
import os

def lambda_handler(event, context):
    bucket_name = event.get('bucket_name', False)
    file_key = event.get('file_key', False)
    vault_name = event.get('vault_name', False)
    stream_name = event.get('stream_name', False)
    if bucket_name and file_key and vault_name:
        try:
            message = 'File from bucket {} with key {} was streamed to elastio stream by name {}'.format(bucket_name, file_key, stream_name)
            status = os.system(f"python3 s3reader.py --bucket_name {bucket_name} --file_key {file_key} | elastio stream backup --stream-name {stream_name} --vault {vault_name}")
            return {"message": f"{message}", "commandStatusCode": status, "statusCode": 200}
        except Exception as e:
            return {"message": f"{e}"}
    else:
        return {
            'message': "Enter s3_url and stream_name and vault name"
        }
        
