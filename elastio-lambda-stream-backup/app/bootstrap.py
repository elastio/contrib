import os
import requests
import sys
import traceback

def run_loop():
       aws_lambda_runtime_api = os.environ['AWS_LAMBDA_RUNTIME_API']
       import app
       while True:
              request_id = None
              try:
                     invocation_response = requests.get(f'http://{aws_lambda_runtime_api}/2018-06-01/runtime/invocation/next')

                     request_id = invocation_response.headers['Lambda-Runtime-Aws-Request-Id']
                     invoked_function_arn = invocation_response.headers['Lambda-Runtime-Invoked-Function-Arn']
                     trace_id = invocation_response.headers['Lambda-Runtime-Trace-Id']
                     os.environ['_X_AMZN_TRACE_ID'] = trace_id
                     
                     context = {
                            'request_id': request_id,
                            'invoked_function_arn': invoked_function_arn,
                            'trace_id': trace_id
                     }
                     
                     event = invocation_response.json()
                     
                     response_url = f'http://{aws_lambda_runtime_api}/2018-06-01/runtime/invocation/{request_id}/response'
                     
                     result = app.lambda_handler(event, context)
                     
                     sys.stdout.flush()

                     requests.post(response_url, json=result)
              
              except:
                      if request_id != None:
                            try:
                                   exc_type, exc_value, exc_traceback = sys.exc_info()
                                   exception_message = {
                                        'errorType': exc_type.__name__,
                                        'errorMessage': str(exc_value),
                                        'stackTrace': traceback.format_exception(exc_type,exc_value, exc_traceback)
                                   }
                                   
                                   error_url = f'http://{aws_lambda_runtime_api}/2018-06-01/runtime/invocation/{request_id}/error'
                                   sys.stdout.flush()
                                   
                                   requests.post(error_url, json=exception_message)
                            except:
                                   pass

run_loop()