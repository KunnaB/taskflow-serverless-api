import json
import os
import sys
import pytest
from unittest.mock import Mock, patch, call

# Set required env vars before import
os.environ['TABLE_NAME'] = 'test-tasks-table'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

# Patch boto3.resource before importing so module-level table init uses mock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../lambda/sqs-worker'))
with patch('boto3.resource'):
    import lambda_function


def _make_sqs_event(records):
    """Wrap message dicts into SQS event Records format"""
    return {
        'Records': [
            {'body': json.dumps(r) if isinstance(r, dict) else r}
            for r in records
        ]
    }


def test_successful_create_message():
    """Test successful processing of a 'create' action message"""
    mock_table = Mock()
    mock_table.put_item.return_value = {}
    lambda_function.table = mock_table

    message = {
        'action': 'create',
        'user_id': 'user-123',
        'task_id': 'task-456',
        'title': 'Buy milk',
        'status': 'incomplete',
        'created_at': '2026-04-07T10:00:00Z'
    }

    result = lambda_function.lambda_handler(_make_sqs_event([message]), None)

    assert result['statusCode'] == 200, f"Expected 200, got {result['statusCode']}"
    mock_table.put_item.assert_called_once_with(Item={
        'user_id': 'user-123',
        'task_id': 'task-456',
        'title': 'Buy milk',
        'status': 'incomplete',
        'created_at': '2026-04-07T10:00:00Z'
    })
    print("✅ Test passed: Create action writes item to DynamoDB and returns 200")


def test_successful_update_message():
    """Test successful processing of an 'update' action message"""
    mock_table = Mock()
    mock_table.update_item.return_value = {}
    lambda_function.table = mock_table

    message = {
        'action': 'update',
        'user_id': 'user-123',
        'task_id': 'task-456',
        'status': 'complete'
    }

    result = lambda_function.lambda_handler(_make_sqs_event([message]), None)

    assert result['statusCode'] == 200, f"Expected 200, got {result['statusCode']}"
    mock_table.update_item.assert_called_once_with(
        Key={'user_id': 'user-123', 'task_id': 'task-456'},
        UpdateExpression='SET #status = :status',
        ExpressionAttributeNames={'#status': 'status'},
        ExpressionAttributeValues={':status': 'complete'}
    )
    print("✅ Test passed: Update action calls update_item on DynamoDB and returns 200")


def test_successful_delete_message():
    """Test successful processing of a 'delete' action message"""
    mock_table = Mock()
    mock_table.delete_item.return_value = {}
    lambda_function.table = mock_table

    message = {
        'action': 'delete',
        'user_id': 'user-123',
        'task_id': 'task-456'
    }

    result = lambda_function.lambda_handler(_make_sqs_event([message]), None)

    assert result['statusCode'] == 200, f"Expected 200, got {result['statusCode']}"
    mock_table.delete_item.assert_called_once_with(
        Key={'user_id': 'user-123', 'task_id': 'task-456'}
    )
    print("✅ Test passed: Delete action calls delete_item on DynamoDB and returns 200")


def test_invalid_json_message_raises():
    """Test that invalid JSON in SQS message body causes an exception (triggers SQS retry)"""
    mock_table = Mock()
    lambda_function.table = mock_table

    event = {
        'Records': [
            {'body': 'this-is-not-valid-json{{{'}
        ]
    }

    raised = False
    try:
        lambda_function.lambda_handler(event, None)
    except Exception:
        raised = True

    assert raised, "Expected exception to be raised for invalid JSON"
    mock_table.put_item.assert_not_called()
    mock_table.update_item.assert_not_called()
    mock_table.delete_item.assert_not_called()
    print("✅ Test passed: Invalid JSON message raises exception for SQS retry/DLQ")


def test_missing_action_field_raises():
    """Test that message missing 'action' field raises KeyError (triggers SQS retry/DLQ)"""
    mock_table = Mock()
    lambda_function.table = mock_table

    message = {
        # 'action' key missing — lambda does message['action'] so this raises KeyError
        'user_id': 'user-123',
        'task_id': 'task-456'
    }

    raised = False
    try:
        lambda_function.lambda_handler(_make_sqs_event([message]), None)
    except Exception:
        raised = True

    assert raised, "Expected KeyError to be raised for missing 'action' field"
    mock_table.put_item.assert_not_called()
    mock_table.update_item.assert_not_called()
    mock_table.delete_item.assert_not_called()
    print("✅ Test passed: Missing 'action' field raises exception for SQS retry/DLQ")


def test_missing_required_fields_in_create_raises():
    """Test that create message missing required fields (e.g. title) raises exception"""
    mock_table = Mock()
    mock_table.put_item.side_effect = Exception("Missing required field")
    lambda_function.table = mock_table

    message = {
        'action': 'create',
        'user_id': 'user-123',
        'task_id': 'task-456'
        # 'title', 'status', 'created_at' missing
    }

    raised = False
    try:
        lambda_function.lambda_handler(_make_sqs_event([message]), None)
    except Exception:
        raised = True

    assert raised, "Expected exception to be raised when required fields are missing"
    print("✅ Test passed: Missing required fields in create message raises exception")


def test_multiple_records_processed():
    """Test that multiple SQS records are all processed"""
    mock_table = Mock()
    mock_table.delete_item.return_value = {}
    lambda_function.table = mock_table

    messages = [
        {'action': 'delete', 'user_id': 'user-1', 'task_id': 'task-1'},
        {'action': 'delete', 'user_id': 'user-2', 'task_id': 'task-2'},
    ]

    result = lambda_function.lambda_handler(_make_sqs_event(messages), None)

    assert result['statusCode'] == 200
    assert mock_table.delete_item.call_count == 2
    print("✅ Test passed: Multiple SQS records are all processed")


def test_dynamodb_write_success_for_create():
    """Test DynamoDB write is called with all required fields for create action"""
    mock_table = Mock()
    mock_table.put_item.return_value = {}
    lambda_function.table = mock_table

    message = {
        'action': 'create',
        'user_id': 'u1',
        'task_id': 't1',
        'title': 'Test task',
        'status': 'incomplete',
        'created_at': '2026-04-07T12:00:00Z'
    }

    lambda_function.lambda_handler(_make_sqs_event([message]), None)

    called_item = mock_table.put_item.call_args[1]['Item']
    assert called_item['user_id'] == 'u1'
    assert called_item['task_id'] == 't1'
    assert called_item['title'] == 'Test task'
    assert called_item['status'] == 'incomplete'
    assert called_item['created_at'] == '2026-04-07T12:00:00Z'
    print("✅ Test passed: DynamoDB put_item called with all required fields")


if __name__ == '__main__':
    test_successful_create_message()
    test_successful_update_message()
    test_successful_delete_message()
    test_invalid_json_message_raises()
    test_missing_action_field_raises()
    test_missing_required_fields_in_create_raises()
    test_multiple_records_processed()
    test_dynamodb_write_success_for_create()
    print("\n✅ All sqs-worker unit tests passed!")
