import json
import sys
import os

from ..lambda_function import lambda_handler

def test_lambda_handler():
    """Test the basic Lambda handler function"""
    #Mock event and context
    event = {"test": "event"}
    context = type('Context', (), {
        'aws_request_id': 'test-request-id',
        'function_name': 'test-function'
    })()

    # Call the handler
    response = lambda_handler(event, context)

    # Assertions
    assert response['statusCode'] == 200
    assert 'message' in json.loads(response['body'])
    assert 'timestamp' in json.loads(response['body'])

if __name__ == '__main__':
    test_lambda_handler()
    print("✅ All tests passed")