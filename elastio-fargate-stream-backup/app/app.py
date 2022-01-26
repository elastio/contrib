import os
import flask
from flask import Flask, render_template, request

app = Flask(__name__)

@app.route('/', methods=['GET'])
def backup():
    if request.values:
        if request.values.get('bucket_name') and \
            request.values.get('file_key') and \
                request.values.get('vault_name') and \
                    request.values.get('stream_name'):
            status = os.system(f"python3 s3reader.py --bucket_name {request.values.get('bucket_name')} --file_key {request.values.get('file_key')} | elastio stream backup --stream-name {request.values.get('stream_name')} --vault {request.values.get('vault_name')}")
            return {"statusCommand": status, "status": 200, "msg": "The file was streamed successfully!."} 
    return {"statusCommand":"statusCommand", "status": 200, "msg": "Enter payload data..."}


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")