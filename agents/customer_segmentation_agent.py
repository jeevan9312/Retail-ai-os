import sys
sys.path.insert(0, '.')
from base_agent import BaseAgent
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

class CustomerSegmentationAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name   = "CustomerSegmentationAgent",
            input_topic  = "retail.customer.events",
            output_topic = "retail.decisions.segmentation"
        )

    def load_data(self):
        sql = """
            SELECT
                CUSTOMER_ID,
                LOYALTY_POINTS,
                APP_SESSION_DURATION,
                LOYALTY_TIER,
                DATEDIFF('day', LAST_PURCHASE_DATE::DATE, CURRENT_DATE()) AS days_since_purchase
            FROM RETAIL_OS_DB.STAGING.STG_CUSTOMER_PROFILES
            WHERE CUSTOMER_ID IS NOT NULL
        """
        return pd.DataFrame(self.query_snowflake(sql))

    def segment_customers(self, df):
        features = ['LOYALTY_POINTS', 'APP_SESSION_DURATION', 'DAYS_SINCE_PURCHASE']
        df_clean = df[features].fillna(0)

        scaler   = StandardScaler()
        X_scaled = scaler.fit_transform(df_clean)

        # K-Means clustering — 4 segments
        kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
        df['cluster'] = kmeans.fit_predict(X_scaled)

        # Label clusters based on loyalty points
        cluster_means = df.groupby('cluster')['LOYALTY_POINTS'].mean()
        sorted_clusters = cluster_means.sort_values(ascending=False)

        labels = {
            sorted_clusters.index[0]: 'CHAMPIONS',
            sorted_clusters.index[1]: 'LOYAL_CUSTOMERS',
            sorted_clusters.index[2]: 'AT_RISK',
            sorted_clusters.index[3]: 'LOST_CUSTOMERS'
        }
        df['segment'] = df['cluster'].map(labels)
        return df

    def run(self):
        print("\n" + "="*50)
        print("  CUSTOMER SEGMENTATION AGENT STARTING")
        print("="*50)

        df = self.load_data()
        print(f"Loaded {len(df)} customers")

        df = self.segment_customers(df)

        segment_counts = df['segment'].value_counts()
        print("\nCustomer Segments:")
        for segment, count in segment_counts.items():
            print(f"   {segment:20s}: {count} customers")

        # Publish segment summaries
        for segment, count in segment_counts.items():
            segment_df = df[df['segment'] == segment]
            decision = {
                'segment':              segment,
                'customer_count':       int(count),
                'avg_loyalty_points':   float(segment_df['LOYALTY_POINTS'].mean()),
                'avg_session_duration': float(segment_df['APP_SESSION_DURATION'].mean()),
                'avg_days_inactive':    float(segment_df['DAYS_SINCE_PURCHASE'].mean()),
                'action':               self.get_action(segment),
            }
            self.publish_decision(decision)

        print(f"\n✅ {self.agent_name} completed!")
        print(f"   Total customers    : {len(df)}")
        print(f"   Segments created   : {len(segment_counts)}")
        return df

    def get_action(self, segment):
        actions = {
            'CHAMPIONS':       'REWARD_WITH_EXCLUSIVE_OFFER',
            'LOYAL_CUSTOMERS': 'UPSELL_PREMIUM_PRODUCTS',
            'AT_RISK':         'SEND_WIN_BACK_CAMPAIGN',
            'LOST_CUSTOMERS':  'SEND_REACTIVATION_EMAIL'
        }
        return actions.get(segment, 'NO_ACTION')

if __name__ == "__main__":
    agent = CustomerSegmentationAgent()
    agent.run()