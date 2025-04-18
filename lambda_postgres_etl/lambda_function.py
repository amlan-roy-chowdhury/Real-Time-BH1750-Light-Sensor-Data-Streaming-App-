import os
import boto3
import psycopg2
import csv
from io import StringIO
from datetime import datetime


s3 = boto3.client('s3')

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
S3_BUCKET = os.getenv("AWS_S3_BUCKET")

def lambda_handler(event, context):
    prefix = "logs/"
    processed = 0

    # Connect to RDS
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cursor = conn.cursor()
    except Exception as e:
        print(f"[ERROR] Could not connect to DB: {e}")
        return {"status": "DB connection error"}

    try:
        response = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix)
        files = [obj['Key'] for obj in response.get('Contents', []) if obj['Key'].endswith('.csv')]

        for key in files:
            print(f"[INFO] Processing file: {key}")
            obj = s3.get_object(Bucket=S3_BUCKET, Key=key)
            content = obj['Body'].read().decode('utf-8')
            reader = csv.reader(StringIO(content))

            headers = next(reader, None)
            data = []

            for row in reader:
                if len(row) == 3 and row[0].isdigit():
                    try:
                        lux = float(row[2])
                        data.append(lux)
                    except:
                        continue

            if not data:
                continue

            min_lux = min(data)
            max_lux = max(data)
            avg_lux = sum(data) / len(data)
            record_count = len(data)

            # Try to infer file date from filename
            file_date = None
            try:
                name = os.path.basename(key)
                date_part = name.split("_")[2].split(".")[0]  # Extract YYYY-MM-DD
                file_date = datetime.strptime(date_part, "%Y-%m-%d").date()
            except:
                file_date = datetime.utcnow().date()

            cursor.execute("""
                INSERT INTO lux_file_summary (filename, file_date, record_count, min_lux, max_lux, avg_lux)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (key, file_date, record_count, min_lux, max_lux, avg_lux))

            conn.commit()
            processed += 1

    except Exception as e:
        print(f"[ERROR] ETL error: {e}")

    finally:
        cursor.close()
        conn.close()

    return {
        "status": "success",
        "files_processed": processed
    }
