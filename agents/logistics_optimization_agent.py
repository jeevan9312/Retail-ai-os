import sys
sys.path.insert(0, '.')
from base_agent import BaseAgent
import pandas as pd
import numpy as np

class LogisticsOptimizationAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name   = "LogisticsOptimizationAgent",
            input_topic  = "retail.inventory.snapshots",
            output_topic = "retail.decisions.logistics"
        )

    def load_data(self):
        sql = """
            SELECT
                w.WAREHOUSE_ID,
                w.WAREHOUSE_NAME,
                w.CITY,
                w.STATE,
                w.CAPACITY_PALLETS,
                w.TEMPERATURE_CONTROLLED,
                COUNT(i.INVENTORY_ID)      AS total_skus,
                SUM(i.CURRENT_STOCK_LEVEL) AS total_stock,
                SUM(CASE WHEN i.NEEDS_REORDER = TRUE
                    THEN 1 ELSE 0 END)     AS items_needing_reorder
            FROM RETAIL_OS_DB.RAW.RAW_WAREHOUSES w
            LEFT JOIN RETAIL_OS_DB.STAGING.FCT_INVENTORY_HEALTH i
                ON w.WAREHOUSE_ID = i.WAREHOUSE_ID
            GROUP BY w.WAREHOUSE_ID, w.WAREHOUSE_NAME,
                     w.CITY, w.STATE,
                     w.CAPACITY_PALLETS, w.TEMPERATURE_CONTROLLED
            ORDER BY items_needing_reorder DESC
        """
        return pd.DataFrame(self.query_snowflake(sql))

    def optimize_routes(self, df):
        routes = []
        warehouses = df.to_dict('records')

        for i, origin in enumerate(warehouses):
            reorder_count = int(origin.get('ITEMS_NEEDING_REORDER') or 0)
            if reorder_count == 0:
                continue

            # Find best destination warehouse (lowest stock)
            others = [w for j, w in enumerate(warehouses) if j != i]
            if not others:
                continue

            destination = min(others,
                key=lambda x: float(x.get('TOTAL_STOCK') or 0))

            priority = 'URGENT' if reorder_count > 50 else \
                       'HIGH'   if reorder_count > 20 else 'NORMAL'

            routes.append({
                'origin_warehouse':      str(origin['WAREHOUSE_ID']),
                'origin_city':           str(origin.get('CITY', '')),
                'destination_warehouse': str(destination['WAREHOUSE_ID']),
                'destination_city':      str(destination.get('CITY', '')),
                'items_to_transfer':     reorder_count,
                'priority':              priority,
                'estimated_cost':        round(reorder_count * 2.5, 2),
                'action':                'DISPATCH_TRANSFER'
            })

        return sorted(routes, key=lambda x: x['items_to_transfer'], reverse=True)

    def run(self):
        print("\n" + "="*50)
        print("  LOGISTICS OPTIMIZATION AGENT STARTING")
        print("="*50)

        df = self.load_data()
        print(f"Loaded {len(df)} warehouses")

        routes  = self.optimize_routes(df)
        urgent  = sum(1 for r in routes if r['priority'] == 'URGENT')
        total_cost = sum(r['estimated_cost'] for r in routes)

        print(f"\nTop 5 Transfer Routes:")
        for r in routes[:5]:
            print(f"  [{r['priority']}] {r['origin_city']} → {r['destination_city']} ({r['items_to_transfer']} items)")
            self.publish_decision(r)

        print(f"\n✅ {self.agent_name} completed!")
        print(f"   Routes optimized   : {len(routes)}")
        print(f"   Urgent transfers   : {urgent}")
        print(f"   Total est. cost    : ${total_cost:,.2f}")
        return routes

if __name__ == "__main__":
    agent = LogisticsOptimizationAgent()
    agent.run()