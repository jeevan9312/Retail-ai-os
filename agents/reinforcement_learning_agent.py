import sys
sys.path.insert(0, '.')
from base_agent import BaseAgent
import pandas as pd
import numpy as np
import random

class ReinforcementLearningAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name   = "ReinforcementLearningAgent",
            input_topic  = "retail.actions.approved",
            output_topic = "retail.decisions.rl_policy"
        )
        self.q_table  = {}
        self.epsilon  = 0.1   # exploration rate
        self.alpha    = 0.1   # learning rate
        self.gamma    = 0.9   # discount factor

    def load_data(self):
        sql = """
            SELECT
                s.PRODUCT_ID,
                s.STORE_ID,
                s.TOTAL_UNITS_SOLD,
                s.TOTAL_NET_REVENUE,
                s.AVG_DISCOUNT,
                i.STOCK_STATUS,
                i.CURRENT_STOCK_LEVEL,
                i.NEEDS_REORDER
            FROM RETAIL_OS_DB.STAGING.FCT_DAILY_SALES s
            LEFT JOIN RETAIL_OS_DB.STAGING.FCT_INVENTORY_HEALTH i
                ON s.PRODUCT_ID = i.PRODUCT_ID
            LIMIT 500
        """
        return pd.DataFrame(self.query_snowflake(sql))

    def get_state(self, row):
        stock  = str(row.get('STOCK_STATUS', 'UNKNOWN'))
        sales  = 'HIGH' if float(row.get('TOTAL_UNITS_SOLD') or 0) > 5 else 'LOW'
        return f"{stock}_{sales}"

    def get_reward(self, row):
        revenue = float(row.get('TOTAL_NET_REVENUE') or 0)
        reorder = bool(row.get('NEEDS_REORDER') or False)
        reward  = revenue * 0.1
        if reorder:
            reward -= 10
        return reward

    def choose_action(self, state):
        actions = ['INCREASE_PRICE', 'DECREASE_PRICE', 'PROMOTE', 'REORDER', 'HOLD']
        if random.random() < self.epsilon:
            return random.choice(actions)
        if state not in self.q_table:
            self.q_table[state] = {a: 0.0 for a in actions}
        return max(self.q_table[state], key=self.q_table[state].get)

    def update_q_table(self, state, action, reward, next_state):
        actions = ['INCREASE_PRICE', 'DECREASE_PRICE', 'PROMOTE', 'REORDER', 'HOLD']
        if state not in self.q_table:
            self.q_table[state] = {a: 0.0 for a in actions}
        if next_state not in self.q_table:
            self.q_table[next_state] = {a: 0.0 for a in actions}
        best_next  = max(self.q_table[next_state].values())
        current_q  = self.q_table[state][action]
        self.q_table[state][action] = current_q + self.alpha * (
            reward + self.gamma * best_next - current_q
        )

    def run(self):
        print("\n" + "="*50)
        print("  REINFORCEMENT LEARNING AGENT STARTING")
        print("="*50)

        df = self.load_data()
        print(f"Loaded {len(df)} state records")

        policies     = []
        total_reward = 0

        rows = df.to_dict('records')
        for i, row in enumerate(rows):
            state      = self.get_state(row)
            action     = self.choose_action(state)
            reward     = self.get_reward(row)
            next_state = self.get_state(rows[min(i+1, len(rows)-1)])
            self.update_q_table(state, action, reward, next_state)
            total_reward += reward

            policies.append({
                'product_id':  str(row.get('PRODUCT_ID', '')),
                'store_id':    str(row.get('STORE_ID', '')),
                'state':       state,
                'action':      action,
                'reward':      round(reward, 2),
                'policy':      'LEARNED'
            })

        # Publish top policies
        for p in policies[:5]:
            self.publish_decision(p)

        # Summary of learned policy
        action_counts = {}
        for p in policies:
            action_counts[p['action']] = action_counts.get(p['action'], 0) + 1

        print(f"\nLearned Policy Summary:")
        for action, count in sorted(action_counts.items(), key=lambda x: -x[1]):
            print(f"  {action:20s}: {count} times")

        print(f"\n✅ {self.agent_name} completed!")
        print(f"   States learned     : {len(self.q_table)}")
        print(f"   Total reward       : {round(total_reward, 2)}")
        print(f"   Policies generated : {len(policies)}")
        return policies

if __name__ == "__main__":
    agent = ReinforcementLearningAgent()
    agent.run()