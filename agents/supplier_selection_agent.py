import sys
sys.path.insert(0, '.')
from base_agent import BaseAgent
import pandas as pd

class SupplierSelectionAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name   = "SupplierSelectionAgent",
            input_topic  = "retail.inventory.snapshots",
            output_topic = "retail.decisions.supplier"
        )

    def load_data(self):
        sql = """
            SELECT
                s.SUPPLIER_ID,
                s.SUPPLIER_NAME,
                s.RELIABILITY_SCORE,
                s.RELIABILITY_TIER,
                s.CITY,
                s.COUNTRY,
                COUNT(b.BATCH_ID)        AS total_batches,
                AVG(b.UNIT_COST)         AS avg_unit_cost,
                AVG(b.PROCUREMENT_COST)  AS avg_procurement_cost
            FROM RETAIL_OS_DB.STAGING.STG_SUPPLIERS s
            LEFT JOIN RETAIL_OS_DB.RAW.RAW_BATCHES b
                ON s.SUPPLIER_ID = b.SUPPLIER_ID
            GROUP BY s.SUPPLIER_ID, s.SUPPLIER_NAME,
                     s.RELIABILITY_SCORE, s.RELIABILITY_TIER,
                     s.CITY, s.COUNTRY
            ORDER BY s.RELIABILITY_SCORE DESC
        """
        return pd.DataFrame(self.query_snowflake(sql))

    def score_suppliers(self, df):
        df = df.copy()
        df['RELIABILITY_SCORE']      = df['RELIABILITY_SCORE'].fillna(0).astype(float)
        df['AVG_UNIT_COST']          = df['AVG_UNIT_COST'].fillna(0).astype(float)
        df['AVG_PROCUREMENT_COST']   = df['AVG_PROCUREMENT_COST'].fillna(0).astype(float)
        df['TOTAL_BATCHES']          = df['TOTAL_BATCHES'].fillna(0).astype(int)

        # Normalize cost (lower is better)
        max_cost = df['AVG_UNIT_COST'].max()
        if max_cost > 0:
            df['cost_score'] = 1 - (df['AVG_UNIT_COST'] / max_cost)
        else:
            df['cost_score'] = 1.0

        # Experience score
        max_batches = df['TOTAL_BATCHES'].max()
        if max_batches > 0:
            df['experience_score'] = df['TOTAL_BATCHES'] / max_batches
        else:
            df['experience_score'] = 0.0

        # Final composite score
        df['composite_score'] = (
            df['RELIABILITY_SCORE'] * 0.5 +
            df['cost_score']        * 0.3 +
            df['experience_score']  * 0.2
        )
        return df.sort_values('composite_score', ascending=False)

    def run(self):
        print("\n" + "="*50)
        print("  SUPPLIER SELECTION AGENT STARTING")
        print("="*50)

        df = self.load_data()
        print(f"Loaded {len(df)} suppliers")

        df = self.score_suppliers(df)

        print("\nTop 5 Recommended Suppliers:")
        for rank, (_, row) in enumerate(df.head(5).iterrows(), 1):
            print(f"  #{rank} {row['SUPPLIER_NAME']} — Score: {row['composite_score']:.2f}")
            decision = {
                'rank':             rank,
                'supplier_id':      str(row['SUPPLIER_ID']),
                'supplier_name':    str(row['SUPPLIER_NAME']),
                'reliability_score': float(row['RELIABILITY_SCORE']),
                'avg_unit_cost':    float(row['AVG_UNIT_COST']),
                'composite_score':  round(float(row['composite_score']), 3),
                'recommendation':   'PRIMARY_SUPPLIER' if rank == 1 else 'BACKUP_SUPPLIER',
                'action':           'USE_FOR_NEXT_PO'
            }
            self.publish_decision(decision)

        print(f"\n✅ {self.agent_name} completed!")
        print(f"   Total suppliers scored : {len(df)}")
        return df

if __name__ == "__main__":
    agent = SupplierSelectionAgent()
    agent.run()