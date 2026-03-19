import sys
sys.path.insert(0, '.')
from base_agent import BaseAgent
import pandas as pd

class SupplyChainRiskAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name   = "SupplyChainRiskAgent",
            input_topic  = "retail.inventory.snapshots",
            output_topic = "retail.decisions.supply_risk"
        )

    def load_data(self):
        sql = """
            SELECT
                r.TRANSACTION_ID,
                r.PRODUCT_ID,
                r.STORE_ID,
                r.SUPPLY_CHAIN_DISRUPTION_RISK,
                r.ANOMALY_DETECTION_FLAG,
                p.PRODUCT_NAME,
                p.CATEGORY,
                p.REQUIRES_REFRIGERATION
            FROM RETAIL_OS_DB.RAW.RAW_RISK_ANOMALY r
            LEFT JOIN RETAIL_OS_DB.STAGING.STG_PRODUCTS p
                ON r.PRODUCT_ID = p.PRODUCT_ID
            WHERE r.SUPPLY_CHAIN_DISRUPTION_RISK > 0.5
            ORDER BY r.SUPPLY_CHAIN_DISRUPTION_RISK DESC
        """
        return pd.DataFrame(self.query_snowflake(sql))

    def assess_risk(self, df):
        risks = []
        for _, row in df.iterrows():
            risk_score  = float(row.get('SUPPLY_CHAIN_DISRUPTION_RISK') or 0)
            refrigerated = bool(row.get('REQUIRES_REFRIGERATION') or False)

            if risk_score > 0.8:
                level  = 'CRITICAL'
                action = 'ACTIVATE_BACKUP_SUPPLIER'
            elif risk_score > 0.65:
                level  = 'HIGH'
                action = 'INCREASE_SAFETY_STOCK'
            else:
                level  = 'MEDIUM'
                action = 'MONITOR_CLOSELY'

            # Extra risk for refrigerated items
            if refrigerated and risk_score > 0.6:
                level  = 'CRITICAL'
                action = 'EMERGENCY_RESTOCK'

            risks.append({
                'product_id':    str(row.get('PRODUCT_ID', '')),
                'store_id':      str(row.get('STORE_ID', '')),
                'product_name':  str(row.get('PRODUCT_NAME', '')),
                'category':      str(row.get('CATEGORY', '')),
                'risk_score':    round(risk_score, 3),
                'risk_level':    level,
                'refrigerated':  refrigerated,
                'action':        action
            })
        return risks

    def run(self):
        print("\n" + "="*50)
        print("  SUPPLY CHAIN RISK AGENT STARTING")
        print("="*50)

        df = self.load_data()
        print(f"Loaded {len(df)} high-risk records")

        risks    = self.assess_risk(df)
        critical = sum(1 for r in risks if r['risk_level'] == 'CRITICAL')
        high     = sum(1 for r in risks if r['risk_level'] == 'HIGH')

        for risk in risks[:10]:
            self.publish_decision(risk)

        print(f"\n✅ {self.agent_name} completed!")
        print(f"   Total risks assessed : {len(risks)}")
        print(f"   Critical risks       : {critical}")
        print(f"   High risks           : {high}")
        return risks

if __name__ == "__main__":
    agent = SupplyChainRiskAgent()
    agent.run()