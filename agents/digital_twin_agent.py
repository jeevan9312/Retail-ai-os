import sys
sys.path.insert(0, '.')
from base_agent import BaseAgent
import pandas as pd
import numpy as np
import simpy
import random

class DigitalTwinAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_name   = "DigitalTwinSimulationAgent",
            input_topic  = "retail.pos.transactions",
            output_topic = "retail.decisions.simulation"
        )

    def load_baseline(self):
        sql = """
            SELECT
                AVG(TOTAL_UNITS_SOLD)    AS avg_daily_demand,
                AVG(TOTAL_NET_REVENUE)   AS avg_daily_revenue,
                AVG(AVG_UNIT_PRICE)      AS avg_price,
                COUNT(DISTINCT STORE_ID) AS total_stores
            FROM RETAIL_OS_DB.STAGING.FCT_DAILY_SALES
        """
        return pd.DataFrame(self.query_snowflake(sql)).iloc[0]

    def simulate_store(self, env, store_id, demand, price,
                       initial_stock, results, duration=30):
        stock   = initial_stock
        revenue = 0
        stockouts = 0

        for day in range(duration):
            # Daily demand with randomness
            daily_demand = max(0, int(np.random.normal(demand, demand * 0.2)))
            sold         = min(daily_demand, stock)
            stock       -= sold
            revenue     += sold * price

            if stock <= 0:
                stockouts += 1
                stock      = initial_stock  # restock

            yield env.timeout(1)

        results[store_id] = {
            'total_revenue': round(revenue, 2),
            'stockout_days': stockouts,
            'final_stock':   stock
        }

    def run_scenario(self, scenario_name, demand_multiplier,
                     price_multiplier, baseline):
        env     = simpy.Environment()
        results = {}

        avg_demand = float(baseline['AVG_DAILY_DEMAND'] or 5)
        avg_price  = float(baseline['AVG_PRICE'] or 5)
        stores     = int(baseline['TOTAL_STORES'] or 10)

        for i in range(min(stores, 10)):
            env.process(self.simulate_store(
                env,
                store_id      = f"STORE_{i+1}",
                demand        = avg_demand * demand_multiplier,
                price         = avg_price  * price_multiplier,
                initial_stock = 100,
                results       = results,
                duration      = 30
            ))

        env.run()

        total_rev   = sum(r['total_revenue'] for r in results.values())
        total_stock = sum(r['stockout_days'] for r in results.values())

        return {
            'scenario':        scenario_name,
            'demand_change':   f"{(demand_multiplier-1)*100:+.0f}%",
            'price_change':    f"{(price_multiplier-1)*100:+.0f}%",
            'projected_revenue': round(total_rev, 2),
            'stockout_days':   total_stock,
            'action':          'SIMULATE_COMPLETE'
        }

    def run(self):
        print("\n" + "="*50)
        print("  DIGITAL TWIN SIMULATION AGENT STARTING")
        print("="*50)

        baseline = self.load_baseline()
        print(f"Baseline: {float(baseline['AVG_DAILY_DEMAND']):.1f} units/day @ ${float(baseline['AVG_PRICE']):.2f}")

        scenarios = [
            ("Baseline",           1.0, 1.0),
            ("Price Cut -10%",     1.2, 0.9),
            ("Price Increase +10%",0.9, 1.1),
            ("Demand Spike +30%",  1.3, 1.0),
            ("Festival Season",    1.5, 1.05),
        ]

        print("\nSimulation Results:")
        print(f"{'Scenario':<25} {'Revenue':>12} {'Stockouts':>10}")
        print("-" * 50)

        for name, demand_mult, price_mult in scenarios:
            result = self.run_scenario(name, demand_mult, price_mult, baseline)
            print(f"  {result['scenario']:<23} ${result['projected_revenue']:>10,.2f} {result['stockout_days']:>8} days")
            self.publish_decision(result)

        print(f"\n✅ {self.agent_name} completed!")
        print(f"   Scenarios simulated : {len(scenarios)}")
        return scenarios

if __name__ == "__main__":
    agent = DigitalTwinAgent()
    agent.run()