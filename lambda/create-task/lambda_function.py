import json
import boto3
import os
import uuid
from datetime import datetime

sqs = boto3.client('sqs')
QUEUE_URL = os.environ['QUEUE_URL']

def lambda_handler(event, context):
    try:
        # Get user ID from Cognito authorizer
        user_id = event['requestContext']['authorizer']['claims']['sub']
        
        # Parse request body
        try:
            body = json.loads(event['body'])
        except (json.JSONDecodeError, KeyError):
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({'error': 'Invalid JSON in request body'})
            }
        
        # Validate required fields
        task_title = body.get('title')
        if not task_title or not task_title.strip():
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({'error': 'Title is required'})
            }
        
        # Create task message
        task_id = str(uuid.uuid4())
        message = {
            'action': 'create',
            'user_id': user_id,
            'task_id': task_id,
            'title': task_title.strip(),
            'status': 'incomplete',
            'created_at': datetime.now().isoformat()
        }
        
        # Send to SQS
        sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps(message)
        )
        
        return {
            'statusCode': 202,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'task_id': task_id,
                'message': 'Task creation queued'
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({'error': 'Internal server error'})
        }
