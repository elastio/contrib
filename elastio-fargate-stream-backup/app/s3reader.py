
import boto3, os
import argparse
parser = argparse.ArgumentParser(
    prog="s3reader",
)
parser.add_argument("--bucket_name", type=str, nargs="?", help="Enter s3 file uri")
parser.add_argument("--file_key", type=str, nargs="?", help="Enter file name if you want to download one of file from zip")
args = parser.parse_args()


def s3reader(bucket_name, file_key):
    session = boto3.Session()
    s3 = session.resource("s3")
    bucket_obj = s3.Object(bucket_name, file_key)
    body = bucket_obj.get()['Body']._raw_stream
    for line in body:
        print(line.decode('utf-8').strip())
    
        

if __name__ == "__main__":
    if args.bucket_name and args.file_key:
        s3reader(bucket_name=args.bucket_name, file_key=args.file_key)