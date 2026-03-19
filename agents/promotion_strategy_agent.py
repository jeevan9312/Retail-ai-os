import sys
sys.path.insert(0, '.')
from base_agent import BaseAgent
import pandas as pd

class PromotionStrategyAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name   = "PromotionStrategyAgent",
            input_topic  = "retail.pos.transactions",
            output_topic = "retail.decisions.promotion"
        )

    def load_data(self):
        sql = """
            SELECT
                e.PRODUCT_ID,
                e.CATEGORY,
                e.PRICE_ELASTICITY_COEFFICIENT,
                e.PROMOTION_LIFT_SCORE,
                e.INVENTORY_TURNOVER_RATIO,
                s.TOTAL_UNITS_SOLD,
                s.TOTAL_NET_REVENUE,
                s.AVG_DISCOUNT,
                i.CURRENT_STOCK_LEVEL
            FROM RETAIL_OS_DB.RAW.RAW_ECONOMIC_SIGNALS e
            LEFT JOIN RETAIL_OS_DB.STAGING.FCT_DAILY_SALES s
                ON e.PRODUCT_ID = s.PRODUCT_ID
            LEFT JOIN RETAIL_OS_DB.STAGING.FCT_INVENTORY_HEALTH i
                ON e.PRODUCT_ID = i.PRODUCT_ID
            WHERE e.PROMOTION_LIFT_SCORE IS NOT NULL
            LIMIT 1000
        """
        return pd.DataFrame(self.query_snowflake(sql))

    def recommend_promotions(self, df):
        recommendations = []

        for _, row in df.iterrows():
            lift      = float(row.get('PROMOTION_LIFT_SCORE') or 0)
            elasticity = float(row.get('PRICE_ELASTICITY_COEFFICIENT') or 0)
            stock     = float(row.get('CURRENT_STOCK_LEVEL') or 0)
            turnover  = float(row.get('INVENTORY_TURNOVER_RATIO') or 0)

            # High lift + elastic = great promotion candidate
            if lift > 2.5 and elasticity < -1.0:
                promo_type  = 'FLASH_SALE_20PCT'
                priority    = 'HIGH'
                expected_lift = round(lift * 1.2, 2)
            elif lift > 1.5 and stock > 100:
                promo_type  = 'BUY_2_GET_1'
                priority    = 'MEDIUM'
                expected_lift = round(lift * 1.1, 2)
            elif turnover < 1.0:
                promo_type  = 'CLEARANCE_SALE'
                priority    = 'HIGH'
                expected_lift = round(lift * 0.9, 2)
            else:
                promo_type  = 'NO_PROMOTION'
                priority    = 'LOW'
                expected_lift = lift

            if promo_type != 'NO_PROMOTION':
                recommendations.append({
                    'product_id':    str(row['PRODUCT_ID']),
                    'category':      str(row.get('CATEGORY', '')),
                    'promotion_type': promo_type,
                    'priority':       priority,
                    'expected_lift':  expected_lift,
                    'current_stock':  int(stock),
                    'action':         'LAUNCH_PROMOTION'
                })

        return recommendations

    def run(self):
        print("\n" + "="*50)
        print("  PROMOTION STRATEGY AGENT STARTING")
        print("="*50)

        df = self.load_data()
        print(f"Loaded {len(df)} product records")

        recs     = self.recommend_promotions(df)
        high     = sum(1 for r in recs if r['priority'] == 'HIGH')
        flash    = sum(1 for r in recs if r['promotion_type'] == 'FLASH_SALE_20PCT')
        clearance = sum(1 for r in recs if r['promotion_type'] == 'CLEARANCE_SALE')

        for rec in recs[:10]:
            self.publish_decision(rec)

        print(f"\n✅ {self.agent_name} completed!")
        print(f"   Total promotions recommended : {len(recs)}")
        print(f"   High priority                : {high}")
        print(f"   Flash sales                  : {flash}")
        print(f"   Clearance sales              : {clearance}")
        return recs

if __name__ == "__main__":
    agent = PromotionStrategyAgent()
    agent.run()