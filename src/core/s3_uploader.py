# src/core/s3_uploader.py
import os
import datetime
import boto3
from config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_BUCKET

s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

def upload_to_s3(filepath):
    filename = os.path.basename(filepath)
    today = datetime.datetime.now()
    s3_key = f"{today.year}/{today.month:02d}/{today.day:02d}/{filename}"

    try:
        s3_client.upload_file(filepath, AWS_S3_BUCKET, s3_key)
        print(f"[S3] Uploaded to: s3://{AWS_S3_BUCKET}/{s3_key}")
    except Exception as e:
        print(f"[S3] Upload failed: {e}")
