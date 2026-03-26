import json
import boto3
import os

sqs = boto3.client('sqs')
QUEUE_URL = os.environ['QUEUE_URL']

def lambda_handler(event, context):
    try:
        # Get user ID and task ID
        user_id = event['requestContext']['authorizer']['claims']['sub']
        task_id = event['pathParameters']['id']
        
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
        
        # Validate status
        status = body.get('status')
        if not status or status not in ['complete', 'incomplete']:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({'error': 'Status must be "complete" or "incomplete"'})
            }
        
        # Create update message
        message = {
            'action': 'update',
            'user_id': user_id,
            'task_id': task_id,
            'status': status
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
            'body': json.dumps({'message': 'Task update queued'})
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
