import boto3
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def upload_to_s3(local_file_path: str, s3_prefix: str):
    """Upload a local CSV file to S3 data lake"""
    
    s3 = boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_REGION')
    )
    
    bucket = os.getenv('S3_BUCKET_NAME')
    file_name = Path(local_file_path).name
    
    # S3 path: raw/transactions/transactions.csv
    s3_key = f"raw/{s3_prefix}/{file_name}"
    
    print(f"Uploading {file_name} → s3://{bucket}/{s3_key}")
    s3.upload_file(local_file_path, bucket, s3_key)
    print(f"✅ Upload complete!")
    
    return f"s3://{bucket}/{s3_key}"

if __name__ == "__main__":
    # Upload all your Fabricate AI files
    files = {
        "data/raw/transactions.csv":  "transactions",
        "data/raw/inventory.csv":     "inventory",
        "data/raw/products.csv":      "products",
        "data/raw/customers.csv":     "customers",
        "data/raw/stores.csv":        "stores",
    }
    
    for local_path, prefix in files.items():
        if Path(local_path).exists():
            upload_to_s3(local_path, prefix)
        else:
            print(f"⚠️  File not found: {local_path}")