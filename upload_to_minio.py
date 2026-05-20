import boto3
import os
from botocore.client import Config

# Connect to MinIO
s3 = boto3.client(
    's3',
    endpoint_url='http://localhost:9000',
    aws_access_key_id='-------',
    aws_secret_access_key='-------',
    config=Config(signature_version='s3v4'),
    region_name='us-east-1'
)

BUCKET = 'retail-ai-os-datalake'
BASE   = r'C:\Users\jeevu\Downloads\retail-ai\retail-ai-os\data'

files = {
    r'Default\transactions.csv':                                         'raw/transactions/transactions.csv',
    r'Derived Features\Economic_Signals.csv':                            'raw/derived_features/Economic_Signals.csv',
    r'Derived Features\Risk_Anomaly.csv':                                'raw/derived_features/Risk_Anomaly.csv',
    r'Derived Features\Sales_Intelligence.csv':                          'raw/derived_features/Sales_Intelligence.csv',
    r'External & Environmental Data Sources\market_competitor_data.csv': 'raw/external/market_competitor_data.csv',
    r'External & Environmental Data Sources\temporal_signals.csv':       'raw/external/temporal_signals.csv',
    r'External & Environmental Data Sources\weather_atmosphere.csv':     'raw/external/weather_atmosphere.csv',
    r'raw\Customer & Digital Interaction Data\customer_profiles.csv':    'raw/customer/customer_profiles.csv',
    r'raw\Customer & Digital Interaction Data\iot_sensor_data.csv':      'raw/customer/iot_sensor_data.csv',
    r'Store & Warehouse Inventory-\batches.csv':                         'raw/warehouse/batches.csv',
    r'Store & Warehouse Inventory-\inventory.csv':                       'raw/warehouse/inventory.csv',
    r'Store & Warehouse Inventory-\products.csv':                        'raw/warehouse/products.csv',
    r'Store & Warehouse Inventory-\supplier_contracts.csv':              'raw/warehouse/supplier_contracts.csv',
    r'Store & Warehouse Inventory-\suppliers.csv':                       'raw/warehouse/suppliers.csv',
    r'Store & Warehouse Inventory-\warehouses.csv':                      'raw/warehouse/warehouses.csv',
}

print("=" * 60)
print("UPLOADING TO MINIO DATA LAKE")
print("=" * 60)

success = 0
failed  = 0

for local_file, s3_path in files.items():
    full_path = os.path.join(BASE, local_file)
    try:
        s3.upload_file(full_path, BUCKET, s3_path)
        print(f"✅ {s3_path}")
        success += 1
    except FileNotFoundError:
        print(f"❌ Not found: {full_path}")
        failed += 1
    except Exception as e:
        print(f"❌ Error: {s3_path} → {e}")
        failed += 1

print("\n" + "=" * 60)
print(f"✅ Uploaded : {success}/15 files")
print(f"❌ Failed   : {failed}/15 files")
print("=" * 60)
print("\nView at: http://localhost:9001")
