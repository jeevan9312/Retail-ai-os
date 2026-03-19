import sys
sys.path.insert(0, '.')
from base_agent import BaseAgent
import pandas as pd
from sklearn.ensemble import IsolationForest

class AnomalyDetectionAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name   = "AnomalyDetectionAgent",
            input_topic  = "retail.pos.transactions",
            output_topic = "retail.decisions.anomaly"
        )

    def load_data(self):
        sql = """
            SELECT
                TRANSACTION_ID,
                PRODUCT_ID,
                STORE_ID,
                FRAUD_PROBABILITY_SCORE,
                SUPPLY_CHAIN_DISRUPTION_RISK,
                ANOMALY_DETECTION_FLAG
            FROM RETAIL_OS_DB.RAW.RAW_RISK_ANOMALY
        """
        return pd.DataFrame(self.query_snowflake(sql))

    def detect_anomalies(self, df):
        features  = ['FRAUD_PROBABILITY_SCORE', 'SUPPLY_CHAIN_DISRUPTION_RISK']
        df_clean  = df[features].fillna(0)

        model     = IsolationForest(contamination=0.05, random_state=42)
        df['anomaly'] = model.fit_predict(df_clean)
        df['score']   = model.decision_function(df_clean)

        anomalies = df[df['anomaly'] == -1].copy()

        results = []
        for _, row in anomalies.iterrows():
            fraud_score   = float(row.get('FRAUD_PROBABILITY_SCORE') or 0)
            supply_risk   = float(row.get('SUPPLY_CHAIN_DISRUPTION_RISK') or 0)

            if fraud_score > 0.7:
                anomaly_type = 'FRAUD_RISK'
            elif supply_risk > 0.7:
                anomaly_type = 'SUPPLY_CHAIN_RISK'
            else:
                anomaly_type = 'GENERAL_ANOMALY'

            results.append({
                'transaction_id':    str(row['TRANSACTION_ID']),
                'product_id':        str(row['PRODUCT_ID']),
                'store_id':          str(row['STORE_ID']),
                'anomaly_type':      anomaly_type,
                'fraud_score':       round(fraud_score, 3),
                'supply_risk':       round(supply_risk, 3),
                'anomaly_score':     round(float(row['score']), 4),
                'action':            'INVESTIGATE_IMMEDIATELY'
            })
        return results

    def run(self):
        print("\n" + "="*50)
        print("  ANOMALY DETECTION AGENT STARTING")
        print("="*50)

        df = self.load_data()
        print(f"Loaded {len(df)} risk records")

        anomalies = self.detect_anomalies(df)
        print(f"Detected {len(anomalies)} anomalies")

        fraud_count  = sum(1 for a in anomalies if a['anomaly_type'] == 'FRAUD_RISK')
        supply_count = sum(1 for a in anomalies if a['anomaly_type'] == 'SUPPLY_CHAIN_RISK')

        for a in anomalies[:10]:
            self.publish_decision(a)

        print(f"\n✅ {self.agent_name} completed!")
        print(f"   Total anomalies    : {len(anomalies)}")
        print(f"   Fraud risks        : {fraud_count}")
        print(f"   Supply chain risks : {supply_count}")
        return anomalies

if __name__ == "__main__":
    agent = AnomalyDetectionAgent()
    agent.run()