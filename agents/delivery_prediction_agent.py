import sys
sys.path.insert(0, '.')
from base_agent import BaseAgent
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

class DeliveryPredictionAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name   = "DeliveryPredictionAgent",
            input_topic  = "retail.inventory.snapshots",
            output_topic = "retail.decisions.delivery"
        )

    def load_data(self):
        sql = """
            SELECT
                b.SUPPLIER_ID,
                b.WAREHOUSE_ID,
                b.RECEIVED_DATE,
                b.EXPIRY_DATE,
                b.QUANTITY,
                b.UNIT_COST,
                b.QUALITY_GRADE,
                s.RELIABILITY_SCORE,
                s.SUPPLIER_NAME
            FROM RETAIL_OS_DB.RAW.RAW_BATCHES b
            LEFT JOIN RETAIL_OS_DB.STAGING.STG_SUPPLIERS s
                ON b.SUPPLIER_ID = s.SUPPLIER_ID
            WHERE b.RECEIVED_DATE IS NOT NULL
            ORDER BY b.RECEIVED_DATE
        """
        return pd.DataFrame(self.query_snowflake(sql))

    def predict_delivery(self, df):
        predictions = []
        for supplier_id, grp in df.groupby('SUPPLIER_ID'):
            reliability = float(grp['RELIABILITY_SCORE'].iloc[0] or 0.5)
            supplier    = str(grp['SUPPLIER_NAME'].iloc[0])
            avg_qty     = float(grp['QUANTITY'].mean())

            # Predict lead time based on reliability
            base_days       = 7
            predicted_days  = round(base_days * (1 + (1 - reliability)), 1)
            on_time_prob    = round(reliability * 100, 1)

            if on_time_prob >= 85:
                delivery_status = 'ON_TIME'
            elif on_time_prob >= 70:
                delivery_status = 'SLIGHT_DELAY'
            else:
                delivery_status = 'LIKELY_DELAYED'

            predictions.append({
                'supplier_id':      str(supplier_id),
                'supplier_name':    supplier,
                'reliability_score': reliability,
                'predicted_lead_days': predicted_days,
                'on_time_probability': on_time_prob,
                'avg_batch_quantity':  round(avg_qty, 0),
                'delivery_status':  delivery_status,
                'action':           'PLAN_AHEAD' if delivery_status != 'ON_TIME' else 'NO_ACTION'
            })
        return predictions

    def run(self):
        print("\n" + "="*50)
        print("  DELIVERY PREDICTION AGENT STARTING")
        print("="*50)

        df = self.load_data()
        print(f"Loaded {len(df)} batch records")

        predictions  = self.predict_delivery(df)
        on_time      = sum(1 for p in predictions if p['delivery_status'] == 'ON_TIME')
        delayed      = sum(1 for p in predictions if p['delivery_status'] == 'LIKELY_DELAYED')

        print("\nDelivery Predictions:")
        for p in predictions[:5]:
            print(f"  {p['supplier_name']:30s} — {p['on_time_probability']}% on-time — {p['delivery_status']}")
            self.publish_decision(p)

        print(f"\n✅ {self.agent_name} completed!")
        print(f"   Total suppliers  : {len(predictions)}")
        print(f"   On Time          : {on_time}")
        print(f"   Likely Delayed   : {delayed}")
        return predictions

if __name__ == "__main__":
    agent = DeliveryPredictionAgent()
    agent.run()