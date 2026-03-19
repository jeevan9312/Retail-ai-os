import sys
sys.path.insert(0, '.')
from base_agent import BaseAgent

class InventoryMonitorAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name   = "InventoryMonitorAgent",
            input_topic  = "retail.inventory.snapshots",
            output_topic = "retail.decisions.reorder"
        )

    def run(self):
        print("\n" + "="*50)
        print("  INVENTORY MONITOR AGENT STARTING")
        print("="*50)
        sql = """
            SELECT PRODUCT_ID, WAREHOUSE_ID, CURRENT_STOCK_LEVEL,
                   REORDER_POINT, SAFETY_STOCK_THRESHOLD,
                   STOCK_STATUS, NEEDS_REORDER
            FROM RETAIL_OS_DB.STAGING.FCT_INVENTORY_HEALTH
            WHERE NEEDS_REORDER = TRUE
            ORDER BY CURRENT_STOCK_LEVEL ASC
        """
        items = self.query_snowflake(sql)
        print(f"Found {len(items)} items needing reorder")
        for item in items[:5]:
            reorder_qty = max(0, (item['SAFETY_STOCK_THRESHOLD'] * 2)
                                - item['CURRENT_STOCK_LEVEL'])
            self.publish_decision({
                'product_id':    item['PRODUCT_ID'],
                'warehouse_id':  item['WAREHOUSE_ID'],
                'stock_status':  item['STOCK_STATUS'],
                'current_stock': item['CURRENT_STOCK_LEVEL'],
                'reorder_qty':   reorder_qty,
                'action':        'CREATE_PURCHASE_ORDER',
                'priority':      'HIGH' if item['STOCK_STATUS'] == 'OUT_OF_STOCK'
                                 else 'MEDIUM'
            })
        print(f"\n✅ Done! Alerts: {len(items)}")
        return items

if __name__ == "__main__":
    agent = InventoryMonitorAgent()
    agent.run()
    