import boto3, os

### function to upload a given file to S3 bucket
def upload_file(file_name, bucket):
    acc = sec = None
    try:
        acc = os.environ['ACCESS_KEY']
        sec = os.environ['SECRET_KEY']
    except: 
        print("Error: ARN, ACCESS_KEY, and SECRET_KEY environment variables must be set")
        return

    s3_client = boto3.client(
        's3',
        region_name='us-west-1',
        aws_access_key_id=acc,
        aws_secret_access_key=sec
    )
    
    object_name = file_name

    response = s3_client.upload_file(file_name, bucket, object_name)

    return response
