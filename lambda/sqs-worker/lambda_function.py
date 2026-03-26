import json
import boto3
import os

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])

def lambda_handler(event, context):
    try:
        for record in event['Records']:
            try:
                message = json.loads(record['body'])
                action = message['action']
                
                if action == 'create':
                    table.put_item(Item={
                        'user_id': message['user_id'],
                        'task_id': message['task_id'],
                        'title': message['title'],
                        'status': message['status'],
                        'created_at': message['created_at']
                    })
                    print(f"Created task {message['task_id']} for user {message['user_id']}")
                    
                elif action == 'update':
                    table.update_item(
                        Key={
                            'user_id': message['user_id'],
                            'task_id': message['task_id']
                        },
                        UpdateExpression='SET #status = :status',
                        ExpressionAttributeNames={'#status': 'status'},
                        ExpressionAttributeValues={':status': message['status']}
                    )
                    print(f"Updated task {message['task_id']} for user {message['user_id']}")
                    
                elif action == 'delete':
                    table.delete_item(
                        Key={
                            'user_id': message['user_id'],
                            'task_id': message['task_id']
                        }
                    )
                    print(f"Deleted task {message['task_id']} for user {message['user_id']}")
                    
            except Exception as e:
                # Log error but don't raise - let DLQ handle after retries
                print(f"Error processing message: {str(e)}")
                print(f"Message: {record['body']}")
                raise  # Re-raise so SQS retries
        
        return {'statusCode': 200}
        
    except Exception as e:
        print(f"Fatal error in worker: {str(e)}")
        raise  # Re-raise for SQS retry/DLQ
