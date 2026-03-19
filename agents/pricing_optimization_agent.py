import sys
sys.path.insert(0, '.')
from base_agent import BaseAgent
import pandas as pd
import numpy as np

class PricingOptimizationAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name   = "PricingOptimizationAgent",
            input_topic  = "retail.pos.transactions",
            output_topic = "retail.decisions.pricing"
        )

    def load_data(self):
        sql = """
            SELECT
                s.PRODUCT_ID,
                s.STORE_ID,
                s.AVG_UNIT_PRICE         AS current_price,
                s.TOTAL_UNITS_SOLD       AS units_sold,
                s.AVG_DISCOUNT           AS avg_discount,
                e.PRICE_ELASTICITY_COEFFICIENT,
                e.PROMOTION_LIFT_SCORE,
                c.COMPETITOR_PRICE,
                c.MARKET_SHARE_PERCENTAGE
            FROM RETAIL_OS_DB.STAGING.FCT_DAILY_SALES s
            LEFT JOIN RETAIL_OS_DB.RAW.RAW_ECONOMIC_SIGNALS e
                ON s.PRODUCT_ID = e.PRODUCT_ID
            LEFT JOIN RETAIL_OS_DB.RAW.RAW_COMPETITOR_DATA c
                ON c.COMPETITOR_ID IS NOT NULL
            LIMIT 1000
        """
        return pd.DataFrame(self.query_snowflake(sql))

    def calculate_optimal_price(self, row):
        current_price = float(row.get('CURRENT_PRICE') or 0)
        competitor    = float(row.get('COMPETITOR_PRICE') or current_price)
        elasticity    = float(row.get('PRICE_ELASTICITY_COEFFICIENT') or -1)
        units_sold    = float(row.get('UNITS_SOLD') or 0)

        if current_price <= 0:
            return current_price, 'NO_CHANGE', 0.0

        # Price vs competitor
        price_diff_pct = ((current_price - competitor) / competitor * 100) if competitor > 0 else 0

        # Determine action
        if price_diff_pct > 15:
            # Our price is 15%+ above competitor — reduce
            optimal     = round(current_price * 0.95, 2)
            action      = 'DECREASE_5PCT'
            confidence  = 0.85
        elif price_diff_pct < -10:
            # Our price is 10%+ below competitor — increase
            optimal     = round(current_price * 1.05, 2)
            action      = 'INCREASE_5PCT'
            confidence  = 0.80
        elif units_sold > 50 and elasticity < -0.5:
            # High demand + elastic — can increase price
            optimal     = round(current_price * 1.03, 2)
            action      = 'INCREASE_3PCT'
            confidence  = 0.75
        else:
            optimal    = current_price
            action     = 'HOLD'
            confidence = 0.90

        return optimal, action, confidence

    def run(self):
        print("\n" + "="*50)
        print("  PRICING OPTIMIZATION AGENT STARTING")
        print("="*50)

        df = self.load_data()
        print(f"Loaded {len(df)} product-store combinations")

        recommendations = []
        action_counts = {}

        for _, row in df.iterrows():
            optimal, action, confidence = self.calculate_optimal_price(row)
            action_counts[action] = action_counts.get(action, 0) + 1

            if action != 'HOLD':
                decision = {
                    'product_id':     str(row.get('PRODUCT_ID', '')),
                    'store_id':       str(row.get('STORE_ID', '')),
                    'current_price':  float(row.get('CURRENT_PRICE') or 0),
                    'optimal_price':  optimal,
                    'action':         action,
                    'confidence':     confidence,
                    'competitor_price': float(row.get('COMPETITOR_PRICE') or 0),
                }
                recommendations.append(decision)

        # Publish top 10
        for rec in recommendations[:10]:
            self.publish_decision(rec)

        print(f"\n✅ {self.agent_name} completed!")
        print(f"   Total analysed     : {len(df)}")
        print(f"   Price changes      : {len(recommendations)}")
        for action, count in action_counts.items():
            print(f"   {action:20s}: {count}")
        return recommendations

if __name__ == "__main__":
    agent = PricingOptimizationAgent()
    agent.run()