import sys
sys.path.insert(0, '.')
from base_agent import BaseAgent
import pandas as pd
import numpy as np

class CampaignAnalyticsAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name   = "CampaignAnalyticsAgent",
            input_topic  = "retail.customer.events",
            output_topic = "retail.decisions.campaign"
        )

    def load_data(self):
        sql = """
            SELECT
                c.CUSTOMER_ID,
                c.DEMOGRAPHIC_SEGMENT,
                c.LOYALTY_POINTS,
                c.LOYALTY_TIER,
                c.APP_SESSION_DURATION,
                t.FESTIVAL_NAME,
                t.IS_HOLIDAY,
                t.SEASON_TYPE,
                t.PROMOTION_EVENT_ID
            FROM RETAIL_OS_DB.STAGING.STG_CUSTOMER_PROFILES c
            CROSS JOIN (
                SELECT FESTIVAL_NAME, IS_HOLIDAY,
                       SEASON_TYPE, PROMOTION_EVENT_ID
                FROM RETAIL_OS_DB.RAW.RAW_TEMPORAL_SIGNALS
                WHERE IS_HOLIDAY = TRUE
                LIMIT 5
            ) t
            LIMIT 1000
        """
        return pd.DataFrame(self.query_snowflake(sql))

    def generate_campaigns(self, df):
        campaigns = []

        # Campaign by loyalty tier
        tier_groups = df.groupby('LOYALTY_TIER').agg({
            'CUSTOMER_ID':       'count',
            'LOYALTY_POINTS':    'mean',
            'APP_SESSION_DURATION': 'mean'
        }).reset_index()

        campaign_map = {
            'GOLD':   ('VIP_EARLY_ACCESS',    'Email + Push + SMS', 'HIGH'),
            'SILVER': ('DOUBLE_POINTS_EVENT', 'Email + Push',       'MEDIUM'),
            'BRONZE': ('WELCOME_DISCOUNT',    'Email',              'LOW'),
        }

        for _, row in tier_groups.iterrows():
            tier    = str(row['LOYALTY_TIER'])
            config  = campaign_map.get(tier, ('GENERIC_PROMO', 'Email', 'LOW'))
            count   = int(row['CUSTOMER_ID'])
            avg_pts = float(row['LOYALTY_POINTS'])

            campaigns.append({
                'campaign_name':    config[0],
                'target_segment':   tier,
                'customer_count':   count,
                'avg_loyalty_pts':  round(avg_pts, 0),
                'channels':         config[1],
                'priority':         config[2],
                'estimated_reach':  count,
                'action':           'LAUNCH_CAMPAIGN'
            })

        # Seasonal campaign
        campaigns.append({
            'campaign_name':   'HOLIDAY_SPECIAL',
            'target_segment':  'ALL_CUSTOMERS',
            'customer_count':  len(df['CUSTOMER_ID'].unique()),
            'channels':        'Email + Push + Social',
            'priority':        'HIGH',
            'estimated_reach': len(df['CUSTOMER_ID'].unique()),
            'action':          'LAUNCH_HOLIDAY_CAMPAIGN'
        })

        return campaigns

    def run(self):
        print("\n" + "="*50)
        print("  CAMPAIGN ANALYTICS AGENT STARTING")
        print("="*50)

        df = self.load_data()
        print(f"Loaded {len(df)} customer-event records")

        campaigns = self.generate_campaigns(df)

        print("\nCampaigns Generated:")
        for c in campaigns:
            print(f"  [{c['priority']}] {c['campaign_name']} → {c['customer_count']} customers via {c['channels']}")
            self.publish_decision(c)

        print(f"\n✅ {self.agent_name} completed!")
        print(f"   Total campaigns : {len(campaigns)}")
        return campaigns

if __name__ == "__main__":
    agent = CampaignAnalyticsAgent()
    agent.run()