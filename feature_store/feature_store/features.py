from datetime import timedelta
from feast import Entity, FeatureView, Field, SnowflakeSource
from feast.types import Float64, Int64, String, Bool

# ── Entities (primary keys) ───────────────────────────────
product = Entity(
    name="product_id",
    description="Product identifier"
)

store = Entity(
    name="store_id",
    description="Store identifier"
)

customer = Entity(
    name="customer_id",
    description="Customer identifier"
)

# ── Data Sources (pointing to Snowflake MARTS) ────────────
daily_sales_source = SnowflakeSource(
    name="daily_sales_source",
    database="RETAIL_OS_DB",
    schema="STAGING",
    table="FCT_DAILY_SALES",
    timestamp_field="DBT_LOADED_AT"
)

inventory_source = SnowflakeSource(
    name="inventory_source",
    database="RETAIL_OS_DB",
    schema="STAGING",
    table="FCT_INVENTORY_HEALTH",
    timestamp_field="DBT_LOADED_AT"
)

customer_source = SnowflakeSource(
    name="customer_source",
    database="RETAIL_OS_DB",
    schema="STAGING",
    table="STG_CUSTOMER_PROFILES",
    timestamp_field="DBT_LOADED_AT"
)

# ── Feature Views ─────────────────────────────────────────
sales_features = FeatureView(
    name="sales_features",
    entities=[product, store],
    ttl=timedelta(days=30),
    source=daily_sales_source,
    schema=[
        Field(name="TOTAL_TRANSACTIONS",  dtype=Int64),
        Field(name="TOTAL_UNITS_SOLD",    dtype=Int64),
        Field(name="TOTAL_GROSS_REVENUE", dtype=Float64),
        Field(name="TOTAL_NET_REVENUE",   dtype=Float64),
        Field(name="AVG_UNIT_PRICE",      dtype=Float64),
        Field(name="AVG_DISCOUNT",        dtype=Float64),
    ]
)

inventory_features = FeatureView(
    name="inventory_features",
    entities=[product],
    ttl=timedelta(days=7),
    source=inventory_source,
    schema=[
        Field(name="CURRENT_STOCK_LEVEL",    dtype=Int64),
        Field(name="SAFETY_STOCK_THRESHOLD", dtype=Int64),
        Field(name="REORDER_POINT",          dtype=Int64),
        Field(name="NEEDS_REORDER",          dtype=Bool),
        Field(name="STOCK_COVERAGE_RATIO",   dtype=Float64),
        Field(name="STOCK_STATUS",           dtype=String),
    ]
)

customer_features = FeatureView(
    name="customer_features",
    entities=[customer],
    ttl=timedelta(days=90),
    source=customer_source,
    schema=[
        Field(name="LOYALTY_POINTS",       dtype=Int64),
        Field(name="APP_SESSION_DURATION", dtype=Float64),
        Field(name="LOYALTY_TIER",         dtype=String),
    ]
)