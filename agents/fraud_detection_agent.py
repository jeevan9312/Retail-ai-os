import sys
sys.path.insert(0, '.')
from base_agent import BaseAgent
import pandas as pd
from sklearn.ensemble import IsolationForest
import numpy as np

class FraudDetectionAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name   = "FraudDetectionAgent",
            input_topic  = "retail.pos.transactions",
            output_topic = "retail.decisions.fraud"
        )
        self.model = None

    def load_data(self):
        sql = """
            SELECT
                t.TRANSACTION_ID,
                t.STORE_ID,
                t.PRODUCT_ID,
                t.QUANTITY_SOLD,
                t.UNIT_PRICE,
                t.DISCOUNT_APPLIED,
                t.PAYMENT_METHOD,
                r.FRAUD_PROBABILITY_SCORE,
                r.ANOMALY_DETECTION_FLAG
            FROM RETAIL_OS_DB.RAW.RAW_TRANSACTIONS t
            LEFT JOIN RETAIL_OS_DB.RAW.RAW_RISK_ANOMALY r
                ON t.TRANSACTION_ID = r.TRANSACTION_ID
        """
        return pd.DataFrame(self.query_snowflake(sql))

    def train_model(self, df):
        features = ['QUANTITY_SOLD', 'UNIT_PRICE', 'DISCOUNT_APPLIED']
        df_clean = df[features].fillna(0)
        self.model = IsolationForest(
            contamination = 0.05,
            random_state  = 42,
            n_estimators  = 100
        )
        self.model.fit(df_clean)
        df['anomaly_score'] = self.model.decision_function(df_clean)
        df['is_fraud']      = self.model.predict(df_clean)
        return df

    def run(self):
        print("\n" + "="*50)
        print("  FRAUD DETECTION AGENT STARTING")
        print("="*50)

        df = self.load_data()
        print(f"Loaded {len(df)} transactions")

        df = self.train_model(df)

        # Find fraudulent transactions
        fraud_cases = df[df['is_fraud'] == -1]
        print(f"Detected {len(fraud_cases)} suspicious transactions")

        alerts = []
        for _, row in fraud_cases.head(10).iterrows():
            decision = {
                'transaction_id':   str(row['TRANSACTION_ID']),
                'store_id':         str(row['STORE_ID']),
                'product_id':       str(row['PRODUCT_ID']),
                'quantity':         float(row['QUANTITY_SOLD']),
                'unit_price':       float(row['UNIT_PRICE']),
                'anomaly_score':    float(row['anomaly_score']),
                'fraud_probability': float(row.get('FRAUD_PROBABILITY_SCORE', 0) or 0),
                'action':           'FLAG_FOR_REVIEW',
                'priority':         'HIGH'
            }
            self.publish_decision(decision)
            alerts.append(decision)

        print(f"\n✅ {self.agent_name} completed!")
        print(f"   Total Transactions : {len(df)}")
        print(f"   Fraud Detected     : {len(fraud_cases)}")
        print(f"   Alerts Published   : {len(alerts)}")
        return alerts

if __name__ == "__main__":
    agent = FraudDetectionAgent()
    agent.run()