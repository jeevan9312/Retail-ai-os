import sys
sys.path.insert(0, '.')
from base_agent import BaseAgent
import pandas as pd

class WarehouseAllocationAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name   = "WarehouseAllocationAgent",
            input_topic  = "retail.inventory.snapshots",
            output_topic = "retail.decisions.warehouse"
        )

    def load_data(self):
        sql = """
            SELECT
                w.WAREHOUSE_ID,
                w.WAREHOUSE_NAME,
                w.CAPACITY_PALLETS,
                w.TEMPERATURE_CONTROLLED,
                w.CITY,
                w.STATE,
                COUNT(i.INVENTORY_ID)       AS total_skus,
                SUM(i.CURRENT_STOCK_LEVEL)  AS total_stock,
                AVG(i.STOCK_COVERAGE_RATIO) AS avg_coverage
            FROM RETAIL_OS_DB.RAW.RAW_WAREHOUSES w
            LEFT JOIN RETAIL_OS_DB.STAGING.FCT_INVENTORY_HEALTH i
                ON w.WAREHOUSE_ID = i.WAREHOUSE_ID
            GROUP BY w.WAREHOUSE_ID, w.WAREHOUSE_NAME,
                     w.CAPACITY_PALLETS, w.TEMPERATURE_CONTROLLED,
                     w.CITY, w.STATE
            ORDER BY w.WAREHOUSE_ID
        """
        return pd.DataFrame(self.query_snowflake(sql))

    def allocate(self, df):
        allocations = []
        for _, row in df.iterrows():
            capacity    = int(row.get('CAPACITY_PALLETS') or 0)
            total_stock = float(row.get('TOTAL_STOCK') or 0)
            total_skus  = int(row.get('TOTAL_SKUS') or 0)
            avg_cov     = float(row.get('AVG_COVERAGE') or 0)

            utilization = round((total_stock / capacity * 100), 1) if capacity > 0 else 0

            if utilization > 90:
                status = 'OVERCAPACITY'
                action = 'TRANSFER_STOCK_OUT'
            elif utilization < 20:
                status = 'UNDERUTILIZED'
                action = 'TRANSFER_STOCK_IN'
            else:
                status = 'OPTIMAL'
                action = 'MAINTAIN'

            allocations.append({
                'warehouse_id':   str(row['WAREHOUSE_ID']),
                'warehouse_name': str(row['WAREHOUSE_NAME']),
                'city':           str(row.get('CITY', '')),
                'capacity':       capacity,
                'total_stock':    int(total_stock),
                'utilization_pct': utilization,
                'total_skus':     total_skus,
                'status':         status,
                'action':         action
            })
        return allocations

    def run(self):
        print("\n" + "="*50)
        print("  WAREHOUSE ALLOCATION AGENT STARTING")
        print("="*50)

        df = self.load_data()
        print(f"Loaded {len(df)} warehouses")

        allocations  = self.allocate(df)
        overcapacity = sum(1 for a in allocations if a['status'] == 'OVERCAPACITY')
        underused    = sum(1 for a in allocations if a['status'] == 'UNDERUTILIZED')
        optimal      = sum(1 for a in allocations if a['status'] == 'OPTIMAL')

        print("\nWarehouse Status:")
        for a in allocations:
            print(f"  {a['warehouse_name']:30s} — {a['utilization_pct']}% used — {a['status']}")
            self.publish_decision(a)

        print(f"\n✅ {self.agent_name} completed!")
        print(f"   Overcapacity  : {overcapacity}")
        print(f"   Underutilized : {underused}")
        print(f"   Optimal       : {optimal}")
        return allocations

if __name__ == "__main__":
    agent = WarehouseAllocationAgent()
    agent.run()