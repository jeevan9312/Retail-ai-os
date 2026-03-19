import sys
sys.path.insert(0, '.')
from base_agent import BaseAgent
import pandas as pd
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_percentage_error


class DemandForecastAgent(BaseAgent):

    def __init__(self):
        super().__init__(
            agent_name="DemandForecastAgent",
            input_topic="retail.pos.transactions",
            output_topic="retail.decisions.demand"
        )
        self.model = None

    def load_data(self):
        sql = """
            SELECT PRODUCT_ID, STORE_ID, TRANSACTION_DATE,
                   TOTAL_UNITS_SOLD, AVG_UNIT_PRICE, AVG_DISCOUNT
            FROM RETAIL_OS_DB.STAGING.FCT_DAILY_SALES
            ORDER BY TRANSACTION_DATE
        """
        return pd.DataFrame(self.query_snowflake(sql))

    def engineer_features(self, df):
        df = df.copy()
        df['TRANSACTION_DATE'] = pd.to_datetime(df['TRANSACTION_DATE'])
        df = df.sort_values(['PRODUCT_ID', 'STORE_ID', 'TRANSACTION_DATE'])
        grp = df.groupby(['PRODUCT_ID', 'STORE_ID'])
        df['day_of_week'] = df['TRANSACTION_DATE'].dt.dayofweek
        df['month'] = df['TRANSACTION_DATE'].dt.month
        df['lag_1d'] = grp['TOTAL_UNITS_SOLD'].shift(1)
        df['lag_7d'] = grp['TOTAL_UNITS_SOLD'].shift(7)
        df['rolling_7d'] = grp['TOTAL_UNITS_SOLD'].transform(
            lambda x: x.shift(1).rolling(3, min_periods=1).mean()
        )
        median = df['TOTAL_UNITS_SOLD'].median()
        df['lag_1d'] = df['lag_1d'].fillna(median)
        df['lag_7d'] = df['lag_7d'].fillna(median)
        df['rolling_7d'] = df['rolling_7d'].fillna(median)
        return df

    def train(self, df):
        features = [
            'day_of_week', 'month', 'lag_1d',
            'lag_7d', 'rolling_7d',
            'AVG_UNIT_PRICE', 'AVG_DISCOUNT'
        ]
        X = df[features]
        y = df['TOTAL_UNITS_SOLD']
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        self.model = XGBRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=5,
            random_state=42
        )
        self.model.fit(X_train, y_train)
        mape = mean_absolute_percentage_error(
            y_test, self.model.predict(X_test)
        )
        print(f"Model MAPE: {mape:.2%}")
        return mape, features

    def generate_forecasts(self, df, features):
        forecasts = []
        for (pid, sid), grp in df.groupby(['PRODUCT_ID', 'STORE_ID']):
            if len(grp) < 1:
                continue
            X_pred = grp[features].iloc[-1].values.reshape(1, -1)
            predicted = max(0, round(float(self.model.predict(X_pred)[0]), 2))
            forecasts.append({
                'product_id': pid,
                'store_id': sid,
                'predicted_demand': predicted,
                'confidence': 0.85
            })
        return forecasts

    def run(self):
        print("\n" + "=" * 50)
        print("  DEMAND FORECAST AGENT STARTING")
        print("=" * 50)
        df = self.load_data()
        print(f"Loaded {len(df)} records")
        df = self.engineer_features(df)
        print(f"Features ready — {len(df)} rows")
        mape, features = self.train(df)
        forecasts = self.generate_forecasts(df, features)
        print(f"Generated {len(forecasts)} forecasts")
        for f in forecasts[:5]:
            self.publish_decision(f)
        print(f"\n✅ Done! MAPE: {mape:.2%}, Forecasts: {len(forecasts)}")
        return forecasts


if __name__ == "__main__":
    agent = DemandForecastAgent()
    agent.run()