import boto3
import pandas as pd
import snowflake.connector
from botocore.client import Config
from io import StringIO

# MinIO connection
s3 = boto3.client(
    's3',
    endpoint_url='http://localhost:9000',
    aws_access_key_id='minioadmin',
    aws_secret_access_key='minioadmin',
    config=Config(signature_version='s3v4'),
    region_name='us-east-1'
)

# Snowflake connection
conn = snowflake.connector.connect(
    account   = 'jneusse-po63749',
    user      = 'JEEVAN17',
    password  = 'Sinchanagowda@123',
    warehouse = 'COMPUTE_WH',
    database  = 'RETAIL_OS_DB',
    schema    = 'RAW'
)

BUCKET = 'retail-ai-os-datalake'

files = {
    'raw/transactions/transactions.csv':              'RAW_TRANSACTIONS',
    'raw/derived_features/Economic_Signals.csv':      'RAW_ECONOMIC_SIGNALS',
    'raw/derived_features/Risk_Anomaly.csv':          'RAW_RISK_ANOMALY',
    'raw/derived_features/Sales_Intelligence.csv':    'RAW_SALES_INTELLIGENCE',
    'raw/external/market_competitor_data.csv':        'RAW_COMPETITOR_DATA',
    'raw/external/temporal_signals.csv':              'RAW_TEMPORAL_SIGNALS',
    'raw/external/weather_atmosphere.csv':            'RAW_WEATHER',
    'raw/customer/customer_profiles.csv':             'RAW_CUSTOMER_PROFILES',
    'raw/customer/iot_sensor_data.csv':               'RAW_IOT_SENSORS',
    'raw/warehouse/batches.csv':                      'RAW_BATCHES',
    'raw/warehouse/inventory.csv':                    'RAW_INVENTORY',
    'raw/warehouse/products.csv':                     'RAW_PRODUCTS',
    'raw/warehouse/supplier_contracts.csv':           'RAW_SUPPLIER_CONTRACTS',
    'raw/warehouse/suppliers.csv':                    'RAW_SUPPLIERS',
    'raw/warehouse/warehouses.csv':                   'RAW_WAREHOUSES',
}

print("=" * 60)
print("LOADING DATA INTO SNOWFLAKE")
print("=" * 60)

from snowflake.connector.pandas_tools import write_pandas

success = 0
failed  = 0

for s3_path, table in files.items():
    try:
        # Read CSV from MinIO
        obj = s3.get_object(Bucket=BUCKET, Key=s3_path)
        df  = pd.read_csv(StringIO(obj['Body'].read().decode('utf-8')))

        # ← KEY FIX: convert all column names to UPPERCASE
        df.columns = [col.upper() for col in df.columns]

        # Write to Snowflake
        write_pandas(
            conn,
            df,
            table,
            auto_create_table=False,
            overwrite=True
        )

        print(f"✅ {table} — {len(df)} rows loaded")
        success += 1

    except Exception as e:
        print(f"❌ {table} — Error: {e}")
        failed += 1

print("\n" + "=" * 60)
print(f"✅ Loaded  : {success}/15 tables")
print(f"❌ Failed  : {failed}/15 tables")
print("=" * 60)

conn.close()
print("\nAll done! Check Snowflake to verify data.")