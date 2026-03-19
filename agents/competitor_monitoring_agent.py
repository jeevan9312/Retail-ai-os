import sys
sys.path.insert(0, '.')
from base_agent import BaseAgent
import pandas as pd

class CompetitorMonitoringAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name   = "CompetitorMonitoringAgent",
            input_topic  = "retail.competitor.prices",
            output_topic = "retail.decisions.competitor"
        )

    def load_data(self):
        sql = """
            SELECT
                COMPETITOR_ID,
                OBSERVATION_DATE,
                COMPETITOR_PRICE,
                MARKET_SHARE_PERCENTAGE,
                TREND_SCORE
            FROM RETAIL_OS_DB.RAW.RAW_COMPETITOR_DATA
            ORDER BY OBSERVATION_DATE DESC
        """
        return pd.DataFrame(self.query_snowflake(sql))

    def analyse(self, df):
        insights = []
        grouped  = df.groupby('COMPETITOR_ID').agg({
            'COMPETITOR_PRICE':        'mean',
            'MARKET_SHARE_PERCENTAGE': 'mean',
            'TREND_SCORE':             'mean'
        }).reset_index()

        for _, row in grouped.iterrows():
            trend    = float(row['TREND_SCORE'])
            share    = float(row['MARKET_SHARE_PERCENTAGE'])
            price    = float(row['COMPETITOR_PRICE'])

            if trend > 0.7:
                threat  = 'HIGH'
                action  = 'REDUCE_PRICE_IMMEDIATELY'
            elif trend > 0.4:
                threat  = 'MEDIUM'
                action  = 'MONITOR_CLOSELY'
            else:
                threat  = 'LOW'
                action  = 'NO_ACTION'

            insights.append({
                'competitor_id':    str(row['COMPETITOR_ID']),
                'avg_price':        round(price, 2),
                'market_share_pct': round(share, 2),
                'trend_score':      round(trend, 2),
                'threat_level':     threat,
                'action':           action,
            })
        return insights

    def run(self):
        print("\n" + "="*50)
        print("  COMPETITOR MONITORING AGENT STARTING")
        print("="*50)

        df = self.load_data()
        print(f"Loaded {len(df)} competitor records")

        insights = self.analyse(df)

        high   = sum(1 for i in insights if i['threat_level'] == 'HIGH')
        medium = sum(1 for i in insights if i['threat_level'] == 'MEDIUM')
        low    = sum(1 for i in insights if i['threat_level'] == 'LOW')

        for insight in insights[:5]:
            self.publish_decision(insight)

        print(f"\n✅ {self.agent_name} completed!")
        print(f"   Competitors analysed : {len(insights)}")
        print(f"   HIGH threat          : {high}")
        print(f"   MEDIUM threat        : {medium}")
        print(f"   LOW threat           : {low}")
        return insights

if __name__ == "__main__":
    agent = CompetitorMonitoringAgent()
    agent.run()