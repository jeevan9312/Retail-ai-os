import pandas as pd
import os

base = r"C:\Users\jeevu\Downloads\retail-ai\retail-ai-os\data"

datasets = {
    "Transactions":       base + r"\Default\transactions.csv",
    "Economic Signals":   base + r"\Derived Features\Economic_Signals.csv",
    "Risk & Anomaly":     base + r"\Derived Features\Risk_Anomaly.csv",
    "Sales Intelligence": base + r"\Derived Features\Sales_Intelligence.csv",
    "Competitor Data":    base + r"\External & Environmental Data Sources\market_competitor_data.csv",
    "Temporal Signals":   base + r"\External & Environmental Data Sources\temporal_signals.csv",
    "Weather":            base + r"\External & Environmental Data Sources\weather_atmosphere.csv",
    "Customer Profiles":  base + r"\raw\Customer & Digital Interaction Data\customer_profiles.csv",
    "IoT Sensors":        base + r"\raw\Customer & Digital Interaction Data\iot_sensor_data.csv",
    "Batches":            base + r"\Store & Warehouse Inventory-\batches.csv",
    "Inventory":          base + r"\Store & Warehouse Inventory-\inventory.csv",
    "Products":           base + r"\Store & Warehouse Inventory-\products.csv",
    "Supplier Contracts": base + r"\Store & Warehouse Inventory-\supplier_contracts.csv",
    "Suppliers":          base + r"\Store & Warehouse Inventory-\suppliers.csv",
    "Warehouses":         base + r"\Store & Warehouse Inventory-\warehouses.csv",
}

print("=" * 60)
print("RETAIL AI OS — DATASET OVERVIEW")
print("=" * 60)

total_rows = 0
for name, path in datasets.items():
    try:
        df = pd.read_csv(path)
        total_rows += len(df)
        print(f"\n✅ {name}")
        print(f"   Rows    : {len(df)}")
        print(f"   Columns : {len(df.columns)}")
        print(f"   Fields  : {', '.join(df.columns.tolist())}")
    except FileNotFoundError:
        print(f"\n❌ {name} — File not found at:")
        print(f"   {path}")

print("\n" + "=" * 60)
print(f"TOTAL RECORDS: {total_rows:,}")
print("=" * 60)