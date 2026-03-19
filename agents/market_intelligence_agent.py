import sys
sys.path.insert(0, '.')
from base_agent import BaseAgent
import pandas as pd

class MarketIntelligenceAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name   = "MarketIntelligenceAgent",
            input_topic  = "retail.competitor.prices",
            output_topic = "retail.decisions.market"
        )

    def load_data(self):
        sql = """
            SELECT
                c.COMPETITOR_ID,
                c.OBSERVATION_DATE,
                c.COMPETITOR_PRICE,
                c.MARKET_SHARE_PERCENTAGE,
                c.TREND_SCORE,
                t.FESTIVAL_NAME,
                t.IS_HOLIDAY,
                t.SEASON_TYPE,
                t.PROMOTION_EVENT_ID
            FROM RETAIL_OS_DB.RAW.RAW_COMPETITOR_DATA c
            LEFT JOIN RETAIL_OS_DB.RAW.RAW_TEMPORAL_SIGNALS t
                ON c.OBSERVATION_DATE = t.OBSERVATION_DATE
            ORDER BY c.OBSERVATION_DATE DESC
            LIMIT 5000
        """
        return pd.DataFrame(self.query_snowflake(sql))

    def generate_intelligence(self, df):
        insights = []

        # Market share analysis
        share_by_competitor = df.groupby('COMPETITOR_ID')['MARKET_SHARE_PERCENTAGE'].mean()
        total_competitor_share = share_by_competitor.sum()
        our_estimated_share = max(0, 100 - total_competitor_share)

        # Seasonal trends
        seasonal = df.groupby('SEASON_TYPE')['COMPETITOR_PRICE'].mean().to_dict()

        # Holiday impact
        holiday_df    = df[df['IS_HOLIDAY'] == True]
        non_holiday   = df[df['IS_HOLIDAY'] == False]
        holiday_price = holiday_df['COMPETITOR_PRICE'].mean() if len(holiday_df) > 0 else 0
        normal_price  = non_holiday['COMPETITOR_PRICE'].mean() if len(non_holiday) > 0 else 0
        holiday_impact = round(((holiday_price - normal_price) / normal_price * 100), 1) if normal_price > 0 else 0

        insights.append({
            'insight_type':         'MARKET_SHARE',
            'our_estimated_share':  round(our_estimated_share, 2),
            'total_competitors':    len(share_by_competitor),
            'market_observation':   'FRAGMENTED' if len(share_by_competitor) > 3 else 'CONCENTRATED',
            'action':               'FOCUS_ON_DIFFERENTIATION'
        })

        insights.append({
            'insight_type':    'HOLIDAY_PRICING',
            'holiday_impact':  holiday_impact,
            'holiday_price':   round(holiday_price, 2),
            'normal_price':    round(normal_price, 2),
            'action':          'INCREASE_PRICE_ON_HOLIDAYS' if holiday_impact > 5 else 'MAINTAIN_PRICE'
        })

        for season, price in seasonal.items():
            if season and str(season) != 'None':
                insights.append({
                    'insight_type':    'SEASONAL_PRICING',
                    'season':          str(season),
                    'avg_competitor_price': round(float(price), 2),
                    'action':          'MATCH_SEASONAL_PRICING'
                })

        return insights

    def run(self):
        print("\n" + "="*50)
        print("  MARKET INTELLIGENCE AGENT STARTING")
        print("="*50)

        df = self.load_data()
        print(f"Loaded {len(df)} market records")

        insights = self.generate_intelligence(df)

        for insight in insights:
            self.publish_decision(insight)
            print(f"  [{insight['insight_type']}] {insight['action']}")

        print(f"\n✅ {self.agent_name} completed!")
        print(f"   Market insights generated : {len(insights)}")
        return insights

if __name__ == "__main__":
    agent = MarketIntelligenceAgent()
    agent.run()