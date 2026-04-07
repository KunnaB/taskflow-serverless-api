import json
import os
import sys
from unittest.mock import Mock, patch

# Set required env vars before import
os.environ['QUEUE_URL'] = 'https://sqs.us-east-1.amazonaws.com/123456789/test-queue'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

# Patch boto3.client before importing so module-level sqs init uses mock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../lambda/delete-task'))
with patch('boto3.client'):
    import lambda_function


def _make_event(user_id='test-user-123', task_id='task-abc'):
    return {
        'requestContext': {
            'authorizer': {
                'claims': {'sub': user_id}
            }
        },
        'pathParameters': {'id': task_id}
    }


def test_successful_deletion():
    """Test successful task deletion returns 202 and queues message"""
    mock_sqs = Mock()
    mock_sqs.send_message.return_value = {'MessageId': 'msg-del-001'}
    lambda_function.sqs = mock_sqs

    response = lambda_function.lambda_handler(_make_event(), None)

    assert response['statusCode'] == 202, f"Expected 202, got {response['statusCode']}"
    body = json.loads(response['body'])
    assert 'message' in body, "Expected message in response body"
    mock_sqs.send_message.assert_called_once()
    print("✅ Test passed: Successful task deletion returns 202 and queues message")


def test_sqs_message_contains_correct_fields():
    """Test that SQS delete message contains correct action, user_id, and task_id"""
    mock_sqs = Mock()
    mock_sqs.send_message.return_value = {'MessageId': 'msg-del-002'}
    lambda_function.sqs = mock_sqs

    response = lambda_function.lambda_handler(
        _make_event(user_id='user-abc', task_id='task-xyz'),
        None
    )

    assert response['statusCode'] == 202
    call_kwargs = mock_sqs.send_message.call_args[1]
    message = json.loads(call_kwargs['MessageBody'])
    assert message['action'] == 'delete'
    assert message['user_id'] == 'user-abc'
    assert message['task_id'] == 'task-xyz'
    print("✅ Test passed: SQS message contains correct delete action and fields")


def test_missing_task_id_returns_500():
    """Test that missing taskId (pathParameters) causes error response"""
    mock_sqs = Mock()
    lambda_function.sqs = mock_sqs

    event = {
        'requestContext': {'authorizer': {'claims': {'sub': 'test-user-123'}}},
        # pathParameters missing
    }

    response = lambda_function.lambda_handler(event, None)

    assert response['statusCode'] == 500, f"Expected 500, got {response['statusCode']}"
    body = json.loads(response['body'])
    assert 'error' in body, "Expected error key in response body"
    mock_sqs.send_message.assert_not_called()
    print("✅ Test passed: Missing taskId returns 500 with error message")


def test_missing_user_id_returns_500():
    """Test that missing userId (authorizer claims) causes error response"""
    mock_sqs = Mock()
    lambda_function.sqs = mock_sqs

    event = {
        'requestContext': {},  # Missing authorizer
        'pathParameters': {'id': 'task-abc'}
    }

    response = lambda_function.lambda_handler(event, None)

    assert response['statusCode'] == 500, f"Expected 500, got {response['statusCode']}"
    body = json.loads(response['body'])
    assert 'error' in body
    mock_sqs.send_message.assert_not_called()
    print("✅ Test passed: Missing userId returns 500 with error message")


def test_missing_path_parameters_key_returns_500():
    """Test that pathParameters key being None/missing causes error"""
    mock_sqs = Mock()
    lambda_function.sqs = mock_sqs

    event = {
        'requestContext': {'authorizer': {'claims': {'sub': 'test-user-123'}}},
        'pathParameters': None
    }

    response = lambda_function.lambda_handler(event, None)

    assert response['statusCode'] == 500, f"Expected 500, got {response['statusCode']}"
    body = json.loads(response['body'])
    assert 'error' in body
    print("✅ Test passed: None pathParameters returns 500")


def test_sqs_exception_returns_500():
    """Test that SQS send failure returns 500"""
    mock_sqs = Mock()
    mock_sqs.send_message.side_effect = Exception("SQS connection error")
    lambda_function.sqs = mock_sqs

    response = lambda_function.lambda_handler(_make_event(), None)

    assert response['statusCode'] == 500, f"Expected 500, got {response['statusCode']}"
    body = json.loads(response['body'])
    assert 'error' in body
    print("✅ Test passed: SQS exception returns 500")


def test_cors_headers_on_success():
    """Test CORS headers are present in 202 success response"""
    mock_sqs = Mock()
    mock_sqs.send_message.return_value = {}
    lambda_function.sqs = mock_sqs

    response = lambda_function.lambda_handler(_make_event(), None)

    assert 'Access-Control-Allow-Origin' in response['headers'], "Missing CORS header"
    assert response['headers']['Access-Control-Allow-Origin'] == '*'
    print("✅ Test passed: CORS headers present in success response")


def test_cors_headers_on_error():
    """Test CORS headers are present in 500 error response"""
    mock_sqs = Mock()
    lambda_function.sqs = mock_sqs

    response = lambda_function.lambda_handler({}, None)

    assert response['statusCode'] == 500
    assert 'Access-Control-Allow-Origin' in response['headers'], "Missing CORS header on error"
    assert response['headers']['Access-Control-Allow-Origin'] == '*'
    print("✅ Test passed: CORS headers present in error response")


if __name__ == '__main__':
    test_successful_deletion()
    test_sqs_message_contains_correct_fields()
    test_missing_task_id_returns_500()
    test_missing_user_id_returns_500()
    test_missing_path_parameters_key_returns_500()
    test_sqs_exception_returns_500()
    test_cors_headers_on_success()
    test_cors_headers_on_error()
    print("\n✅ All delete-task unit tests passed!")
