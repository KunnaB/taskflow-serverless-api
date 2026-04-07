import json
import os
import sys
from unittest.mock import Mock, patch

# Set required env vars before import
os.environ['QUEUE_URL'] = 'https://sqs.us-east-1.amazonaws.com/123456789/test-queue'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

# Patch boto3.client before importing so module-level sqs init uses mock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../lambda/update-task'))
with patch('boto3.client'):
    import lambda_function


def _make_event(user_id='test-user-123', task_id='task-abc', body=None):
    return {
        'requestContext': {
            'authorizer': {
                'claims': {'sub': user_id}
            }
        },
        'pathParameters': {'id': task_id},
        'body': json.dumps(body) if body is not None else json.dumps({'status': 'complete'})
    }


def test_successful_update_complete():
    """Test successful task update to 'complete' status"""
    mock_sqs = Mock()
    mock_sqs.send_message.return_value = {'MessageId': 'msg-001'}
    lambda_function.sqs = mock_sqs

    response = lambda_function.lambda_handler(_make_event(body={'status': 'complete'}), None)

    assert response['statusCode'] == 202, f"Expected 202, got {response['statusCode']}"
    body = json.loads(response['body'])
    assert 'message' in body, "Expected message in response body"
    mock_sqs.send_message.assert_called_once()
    print("✅ Test passed: Successful update to 'complete' returns 202")


def test_successful_update_incomplete():
    """Test successful task update to 'incomplete' status"""
    mock_sqs = Mock()
    mock_sqs.send_message.return_value = {'MessageId': 'msg-002'}
    lambda_function.sqs = mock_sqs

    response = lambda_function.lambda_handler(_make_event(body={'status': 'incomplete'}), None)

    assert response['statusCode'] == 202, f"Expected 202, got {response['statusCode']}"
    print("✅ Test passed: Successful update to 'incomplete' returns 202")


def test_invalid_status_returns_400():
    """Test that invalid status value returns 400"""
    mock_sqs = Mock()
    lambda_function.sqs = mock_sqs

    response = lambda_function.lambda_handler(_make_event(body={'status': 'invalid-status'}), None)

    assert response['statusCode'] == 400, f"Expected 400, got {response['statusCode']}"
    body = json.loads(response['body'])
    assert 'error' in body, "Expected error in response body"
    mock_sqs.send_message.assert_not_called()
    print("✅ Test passed: Invalid status returns 400")


def test_missing_status_returns_400():
    """Test that missing status field returns 400"""
    mock_sqs = Mock()
    lambda_function.sqs = mock_sqs

    response = lambda_function.lambda_handler(_make_event(body={'title': 'No status here'}), None)

    assert response['statusCode'] == 400, f"Expected 400, got {response['statusCode']}"
    body = json.loads(response['body'])
    assert 'error' in body
    print("✅ Test passed: Missing status field returns 400")


def test_invalid_json_body_returns_400():
    """Test that malformed JSON body returns 400"""
    mock_sqs = Mock()
    lambda_function.sqs = mock_sqs

    event = {
        'requestContext': {'authorizer': {'claims': {'sub': 'test-user-123'}}},
        'pathParameters': {'id': 'task-abc'},
        'body': 'not-valid-json{'
    }

    response = lambda_function.lambda_handler(event, None)

    assert response['statusCode'] == 400, f"Expected 400, got {response['statusCode']}"
    body = json.loads(response['body'])
    assert 'error' in body
    print("✅ Test passed: Invalid JSON body returns 400")


def test_missing_task_id_returns_500():
    """Test that missing taskId (pathParameters) causes error"""
    mock_sqs = Mock()
    lambda_function.sqs = mock_sqs

    event = {
        'requestContext': {'authorizer': {'claims': {'sub': 'test-user-123'}}},
        # pathParameters missing entirely
        'body': json.dumps({'status': 'complete'})
    }

    response = lambda_function.lambda_handler(event, None)

    assert response['statusCode'] == 500, f"Expected 500, got {response['statusCode']}"
    body = json.loads(response['body'])
    assert 'error' in body
    print("✅ Test passed: Missing taskId returns 500 with error message")


def test_sqs_message_contains_correct_fields():
    """Test that the SQS message is sent with correct action and fields"""
    mock_sqs = Mock()
    mock_sqs.send_message.return_value = {'MessageId': 'msg-003'}
    lambda_function.sqs = mock_sqs

    response = lambda_function.lambda_handler(
        _make_event(user_id='user-xyz', task_id='task-999', body={'status': 'complete'}),
        None
    )

    assert response['statusCode'] == 202
    call_kwargs = mock_sqs.send_message.call_args[1]
    message = json.loads(call_kwargs['MessageBody'])
    assert message['action'] == 'update'
    assert message['user_id'] == 'user-xyz'
    assert message['task_id'] == 'task-999'
    assert message['status'] == 'complete'
    print("✅ Test passed: SQS message contains correct action and fields")


def test_cors_headers_on_success():
    """Test CORS headers present in 202 response"""
    mock_sqs = Mock()
    mock_sqs.send_message.return_value = {}
    lambda_function.sqs = mock_sqs

    response = lambda_function.lambda_handler(_make_event(), None)

    assert 'Access-Control-Allow-Origin' in response['headers']
    assert response['headers']['Access-Control-Allow-Origin'] == '*'
    print("✅ Test passed: CORS headers present in success response")


def test_cors_headers_on_error():
    """Test CORS headers present in 400 error response"""
    mock_sqs = Mock()
    lambda_function.sqs = mock_sqs

    response = lambda_function.lambda_handler(_make_event(body={'status': 'bad'}), None)

    assert response['statusCode'] == 400
    assert 'Access-Control-Allow-Origin' in response['headers']
    assert response['headers']['Access-Control-Allow-Origin'] == '*'
    print("✅ Test passed: CORS headers present in error response")


if __name__ == '__main__':
    test_successful_update_complete()
    test_successful_update_incomplete()
    test_invalid_status_returns_400()
    test_missing_status_returns_400()
    test_invalid_json_body_returns_400()
    test_missing_task_id_returns_500()
    test_sqs_message_contains_correct_fields()
    test_cors_headers_on_success()
    test_cors_headers_on_error()
    print("\n✅ All update-task unit tests passed!")
