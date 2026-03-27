import json
import os
import sys
from unittest.mock import Mock, patch

# Add lambda to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../lambda/create-task'))

def test_empty_title_returns_400():
    """Test that empty title returns 400 error"""
    # Set required env vars
    os.environ['QUEUE_URL'] = 'https://sqs.us-east-1.amazonaws.com/123/test'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
    
    # Mock boto3 before importing lambda_function
    with patch('boto3.client') as mock_client:
        from lambda_function import lambda_handler
        
        # Mock event
        event = {
            'requestContext': {
                'authorizer': {
                    'claims': {'sub': 'test-user-123'}
                }
            },
            'body': json.dumps({'title': ''})
        }
        
        response = lambda_handler(event, None)
        
        assert response['statusCode'] == 400, f"Expected 400, got {response['statusCode']}"
        assert 'error' in json.loads(response['body']), "Expected error in response"
        print("✅ Test passed: Empty title returns 400")

def test_valid_title_format():
    """Test that valid title passes validation"""
    os.environ['QUEUE_URL'] = 'https://sqs.us-east-1.amazonaws.com/123/test'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
    
    with patch('boto3.client') as mock_client:
        # Mock SQS send_message
        mock_sqs = Mock()
        mock_sqs.send_message.return_value = {}
        mock_client.return_value = mock_sqs
        
        from lambda_function import lambda_handler
        
        event = {
            'requestContext': {
                'authorizer': {
                    'claims': {'sub': 'test-user-123'}
                }
            },
            'body': json.dumps({'title': 'Buy groceries'})
        }
        
        response = lambda_handler(event, None)
        
        # Should return 202 (accepted) if validation passed
        assert response['statusCode'] == 202, f"Expected 202, got {response['statusCode']}"
        print("✅ Test passed: Valid title accepted and queued")

if __name__ == '__main__':
    test_empty_title_returns_400()
    test_valid_title_format()
    print("\n✅ All unit tests passed!")
