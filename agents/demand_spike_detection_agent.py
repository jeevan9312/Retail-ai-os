import sys
sys.path.insert(0, '.')
from base_agent import BaseAgent
import pandas as pd
import numpy as np

class DemandSpikeDetectionAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name   = "DemandSpikeDetectionAgent",
            input_topic  = "retail.pos.transactions",
            output_topic = "retail.decisions.demand_spike"
        )

    def load_data(self):
        sql = """
            SELECT
                PRODUCT_ID,
                STORE_ID,
                TRANSACTION_DATE,
                TOTAL_UNITS_SOLD,
                TOTAL_NET_REVENUE
            FROM RETAIL_OS_DB.STAGING.FCT_DAILY_SALES
            ORDER BY TRANSACTION_DATE
        """
        return pd.DataFrame(self.query_snowflake(sql))

    def detect_spikes(self, df):
        spikes = []
        for (pid, sid), grp in df.groupby(['PRODUCT_ID', 'STORE_ID']):
            if len(grp) < 5:
                continue
            grp       = grp.sort_values('TRANSACTION_DATE')
            mean_sales = grp['TOTAL_UNITS_SOLD'].mean()
            std_sales  = grp['TOTAL_UNITS_SOLD'].std()
            latest     = float(grp['TOTAL_UNITS_SOLD'].iloc[-1])

            # Spike = latest sales > mean + 2 standard deviations
            threshold  = mean_sales + (2 * std_sales)
            if latest > threshold and std_sales > 0:
                spike_pct = round(((latest - mean_sales) / mean_sales) * 100, 1)
                spikes.append({
                    'product_id':   str(pid),
                    'store_id':     str(sid),
                    'latest_sales': latest,
                    'avg_sales':    round(float(mean_sales), 2),
                    'spike_pct':    spike_pct,
                    'severity':     'CRITICAL' if spike_pct > 100 else 'HIGH',
                    'action':       'INCREASE_STOCK_IMMEDIATELY'
                })
        return spikes

    def run(self):
        print("\n" + "="*50)
        print("  DEMAND SPIKE DETECTION AGENT STARTING")
        print("="*50)

        df = self.load_data()
        print(f"Loaded {len(df)} daily sales records")

        spikes = self.detect_spikes(df)
        print(f"Detected {len(spikes)} demand spikes")

        for spike in spikes[:10]:
            self.publish_decision(spike)

        critical = sum(1 for s in spikes if s['severity'] == 'CRITICAL')
        print(f"\n✅ {self.agent_name} completed!")
        print(f"   Total spikes detected : {len(spikes)}")
        print(f"   Critical spikes       : {critical}")
        return spikes

if __name__ == "__main__":
    agent = DemandSpikeDetectionAgent()
    agent.run()