import snowflake.connector

try:
    conn = snowflake.connector.connect(
        account   = 'jneusse-po63749',  # from your URL
        user      = 'JEEVAN17',          # your login username
        password  = '---------',     # your password
        warehouse = 'COMPUTE_WH',
        database  = 'RETAIL_OS_DB',
        schema    = 'RAW'
    )
    print("✅ Connected to Snowflake successfully!")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM RAW_TRANSACTIONS")
    print(f"Rows in RAW_TRANSACTIONS: {cursor.fetchone()[0]}")
    conn.close()

except Exception as e:
    print(f"❌ Connection failed: {e}")
