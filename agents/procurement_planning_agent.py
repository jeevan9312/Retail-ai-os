import sys
sys.path.insert(0, '.')
from base_agent import BaseAgent
import pandas as pd

class ProcurementPlanningAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name   = "ProcurementPlanningAgent",
            input_topic  = "retail.inventory.snapshots",
            output_topic = "retail.decisions.procurement"
        )

    def load_data(self):
        sql = """
            SELECT
                i.PRODUCT_ID,
                i.WAREHOUSE_ID,
                i.CURRENT_STOCK_LEVEL,
                i.REORDER_POINT,
                i.SAFETY_STOCK_THRESHOLD,
                i.LEAD_TIME_DAYS,
                i.STOCK_STATUS,
                i.NEEDS_REORDER,
                p.PRODUCT_NAME,
                p.CATEGORY
            FROM RETAIL_OS_DB.STAGING.FCT_INVENTORY_HEALTH i
            LEFT JOIN RETAIL_OS_DB.STAGING.STG_PRODUCTS p
                ON i.PRODUCT_ID = p.PRODUCT_ID
            WHERE i.NEEDS_REORDER = TRUE
            ORDER BY i.CURRENT_STOCK_LEVEL ASC
        """
        return pd.DataFrame(self.query_snowflake(sql))

    def calculate_eoq(self, demand, ordering_cost=50, holding_cost=2):
        # Economic Order Quantity formula
        import math
        if demand <= 0:
            return 0
        return round(math.sqrt((2 * demand * ordering_cost) / holding_cost))

    def create_procurement_plan(self, df):
        plans = []
        for _, row in df.iterrows():
            current = int(row.get('CURRENT_STOCK_LEVEL') or 0)
            safety  = int(row.get('SAFETY_STOCK_THRESHOLD') or 50)
            lead    = int(row.get('LEAD_TIME_DAYS') or 7)

            # Estimate daily demand
            daily_demand = max(1, safety // 30)
            eoq          = self.calculate_eoq(daily_demand * 30)
            order_qty    = max(eoq, (safety * 2) - current)

            urgency = 'CRITICAL' if row.get('STOCK_STATUS') == 'OUT_OF_STOCK' else \
                      'HIGH'     if row.get('STOCK_STATUS') == 'REORDER_NOW'  else 'MEDIUM'

            plans.append({
                'product_id':    str(row['PRODUCT_ID']),
                'warehouse_id':  str(row['WAREHOUSE_ID']),
                'product_name':  str(row.get('PRODUCT_NAME', '')),
                'category':      str(row.get('CATEGORY', '')),
                'current_stock': current,
                'order_quantity': order_qty,
                'lead_time_days': lead,
                'urgency':       urgency,
                'action':        'CREATE_PURCHASE_ORDER'
            })
        return plans

    def run(self):
        print("\n" + "="*50)
        print("  PROCUREMENT PLANNING AGENT STARTING")
        print("="*50)

        df = self.load_data()
        print(f"Found {len(df)} items needing procurement")

        plans    = self.create_procurement_plan(df)
        critical = sum(1 for p in plans if p['urgency'] == 'CRITICAL')
        high     = sum(1 for p in plans if p['urgency'] == 'HIGH')

        for plan in plans[:10]:
            self.publish_decision(plan)

        print(f"\n✅ {self.agent_name} completed!")
        print(f"   Total POs planned  : {len(plans)}")
        print(f"   Critical           : {critical}")
        print(f"   High               : {high}")
        return plans

if __name__ == "__main__":
    agent = ProcurementPlanningAgent()
    agent.run()