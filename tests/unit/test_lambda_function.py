"""
Unit tests for Lambda function handler.
"""
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lambda_function import lambda_handler


def test_lambda_handler():
    """Test the basic Lambda handler function"""
    # Mock event and context
    event = {"test": "event"}
    context = type('Context', (), {
        'aws_request_id': 'test-request-id',
        'function_name': 'test-function'
    })()

    # Call the handler
    response = lambda_handler(event, context)

    # Assertions
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert 'message' in body
    assert 'request_id' in body
    assert body['request_id'] == 'test-request-id'


if __name__ == '__main__':
    test_lambda_handler()
    print("✅ All tests passed")
