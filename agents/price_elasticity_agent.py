import sys
sys.path.insert(0, '.')
from base_agent import BaseAgent
import pandas as pd
import numpy as np

class PriceElasticityAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name   = "PriceElasticityAgent",
            input_topic  = "retail.pos.transactions",
            output_topic = "retail.decisions.elasticity"
        )

    def load_data(self):
        sql = """
            SELECT
                e.PRODUCT_ID,
                e.STORE_ID,
                e.CATEGORY,
                e.PRICE_ELASTICITY_COEFFICIENT,
                e.PROMOTION_LIFT_SCORE,
                e.INVENTORY_TURNOVER_RATIO,
                s.AVG_UNIT_PRICE,
                s.TOTAL_UNITS_SOLD
            FROM RETAIL_OS_DB.RAW.RAW_ECONOMIC_SIGNALS e
            LEFT JOIN RETAIL_OS_DB.STAGING.FCT_DAILY_SALES s
                ON e.PRODUCT_ID = s.PRODUCT_ID
                AND e.STORE_ID  = s.STORE_ID
            WHERE e.PRICE_ELASTICITY_COEFFICIENT IS NOT NULL
            LIMIT 2000
        """
        return pd.DataFrame(self.query_snowflake(sql))

    def analyse_elasticity(self, df):
        results = []
        for (pid, cat), grp in df.groupby(['PRODUCT_ID', 'CATEGORY']):
            elasticity = float(grp['PRICE_ELASTICITY_COEFFICIENT'].mean())
            promo_lift = float(grp['PROMOTION_LIFT_SCORE'].mean())
            turnover   = float(grp['INVENTORY_TURNOVER_RATIO'].mean())

            if elasticity < -1.5:
                sensitivity = 'HIGHLY_ELASTIC'
                action      = 'REDUCE_PRICE_FOR_VOLUME'
            elif elasticity < -0.5:
                sensitivity = 'ELASTIC'
                action      = 'CONSIDER_PROMOTION'
            elif elasticity > -0.5:
                sensitivity = 'INELASTIC'
                action      = 'INCREASE_PRICE_SAFELY'
            else:
                sensitivity = 'UNIT_ELASTIC'
                action      = 'MAINTAIN_PRICE'

            results.append({
                'product_id':    str(pid),
                'category':      str(cat),
                'elasticity':    round(elasticity, 3),
                'promo_lift':    round(promo_lift, 3),
                'turnover':      round(turnover, 3),
                'sensitivity':   sensitivity,
                'action':        action
            })
        return results

    def run(self):
        print("\n" + "="*50)
        print("  PRICE ELASTICITY AGENT STARTING")
        print("="*50)

        df = self.load_data()
        print(f"Loaded {len(df)} economic signal records")

        results       = self.analyse_elasticity(df)
        highly_elastic = sum(1 for r in results if r['sensitivity'] == 'HIGHLY_ELASTIC')
        inelastic      = sum(1 for r in results if r['sensitivity'] == 'INELASTIC')

        for r in results[:10]:
            self.publish_decision(r)

        print(f"\n✅ {self.agent_name} completed!")
        print(f"   Products analysed  : {len(results)}")
        print(f"   Highly Elastic     : {highly_elastic}")
        print(f"   Inelastic          : {inelastic}")
        return results

if __name__ == "__main__":
    agent = PriceElasticityAgent()
    agent.run()