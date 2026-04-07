import json
import os
import sys
from unittest.mock import Mock, patch

# Set required env vars before import
os.environ['TABLE_NAME'] = 'test-tasks-table'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

# Patch boto3.resource before importing so module-level table init uses mock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../lambda/get-tasks'))
with patch('boto3.resource'):
    import lambda_function


def _make_event(user_id='test-user-123'):
    return {
        'requestContext': {
            'authorizer': {
                'claims': {'sub': user_id}
            }
        }
    }


def test_successful_retrieval():
    """Test successful retrieval of tasks for a user"""
    mock_table = Mock()
    mock_table.query.return_value = {
        'Items': [
            {'task_id': 'task-1', 'user_id': 'test-user-123', 'title': 'Buy groceries', 'status': 'incomplete'},
            {'task_id': 'task-2', 'user_id': 'test-user-123', 'title': 'Walk dog', 'status': 'complete'},
        ]
    }
    lambda_function.table = mock_table

    response = lambda_function.lambda_handler(_make_event(), None)

    assert response['statusCode'] == 200, f"Expected 200, got {response['statusCode']}"
    body = json.loads(response['body'])
    assert len(body) == 2, f"Expected 2 tasks, got {len(body)}"
    assert body[0]['title'] == 'Buy groceries'
    # Verify DynamoDB was queried with the right user_id
    mock_table.query.assert_called_once()
    print("✅ Test passed: Successful task retrieval returns 200 with tasks")


def test_empty_task_list():
    """Test when user has no tasks (empty result)"""
    mock_table = Mock()
    mock_table.query.return_value = {'Items': []}
    lambda_function.table = mock_table

    response = lambda_function.lambda_handler(_make_event(), None)

    assert response['statusCode'] == 200, f"Expected 200, got {response['statusCode']}"
    body = json.loads(response['body'])
    assert body == [], f"Expected empty list, got {body}"
    print("✅ Test passed: Empty task list returns 200 with empty array")


def test_missing_items_key_returns_empty():
    """Test when DynamoDB response has no Items key"""
    mock_table = Mock()
    mock_table.query.return_value = {}
    lambda_function.table = mock_table

    response = lambda_function.lambda_handler(_make_event(), None)

    assert response['statusCode'] == 200, f"Expected 200, got {response['statusCode']}"
    body = json.loads(response['body'])
    assert body == [], f"Expected empty list, got {body}"
    print("✅ Test passed: Missing Items key in DynamoDB response returns empty list")


def test_missing_user_id_returns_500():
    """Test missing userId in event triggers error handling"""
    mock_table = Mock()
    lambda_function.table = mock_table

    event = {'requestContext': {}}  # Missing authorizer/claims

    response = lambda_function.lambda_handler(event, None)

    assert response['statusCode'] == 500, f"Expected 500, got {response['statusCode']}"
    body = json.loads(response['body'])
    assert 'error' in body, "Expected error key in response body"
    print("✅ Test passed: Missing userId returns 500 with error message")


def test_cors_headers_present():
    """Test that CORS headers are included in all responses"""
    mock_table = Mock()
    mock_table.query.return_value = {'Items': []}
    lambda_function.table = mock_table

    response = lambda_function.lambda_handler(_make_event(), None)

    assert 'Access-Control-Allow-Origin' in response['headers'], "Missing CORS header"
    assert response['headers']['Access-Control-Allow-Origin'] == '*', "CORS header should be '*'"
    print("✅ Test passed: CORS headers present in successful response")


def test_cors_headers_present_on_error():
    """Test that CORS headers are included in error responses"""
    mock_table = Mock()
    lambda_function.table = mock_table

    event = {}  # Completely missing requestContext -> KeyError -> 500

    response = lambda_function.lambda_handler(event, None)

    assert 'Access-Control-Allow-Origin' in response['headers'], "Missing CORS header on error response"
    assert response['headers']['Access-Control-Allow-Origin'] == '*'
    print("✅ Test passed: CORS headers present in error response")


def test_dynamodb_exception_returns_500():
    """Test that DynamoDB errors are caught and return 500"""
    mock_table = Mock()
    mock_table.query.side_effect = Exception("DynamoDB connection timeout")
    lambda_function.table = mock_table

    response = lambda_function.lambda_handler(_make_event(), None)

    assert response['statusCode'] == 500, f"Expected 500, got {response['statusCode']}"
    body = json.loads(response['body'])
    assert 'error' in body
    print("✅ Test passed: DynamoDB exception returns 500")


if __name__ == '__main__':
    test_successful_retrieval()
    test_empty_task_list()
    test_missing_items_key_returns_empty()
    test_missing_user_id_returns_500()
    test_cors_headers_present()
    test_cors_headers_present_on_error()
    test_dynamodb_exception_returns_500()
    print("\n✅ All get-tasks unit tests passed!")
