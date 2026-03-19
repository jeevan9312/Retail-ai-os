import sys
sys.path.insert(0, '.')
import json
import snowflake.connector
from kafka import KafkaConsumer, KafkaProducer
from datetime import datetime

class DecisionEngine:
    def __init__(self):
        # Kafka consumer — reads from all agent decision topics
        self.consumer = KafkaConsumer(
            'retail.decisions.demand',
            'retail.decisions.reorder',
            bootstrap_servers='localhost:9092',
            value_deserializer=lambda v: json.loads(v.decode('utf-8')),
            auto_offset_reset='earliest',
            consumer_timeout_ms=5000,
            group_id='decision_engine'
        )

        # Kafka producer — publishes approved actions
        self.producer = KafkaProducer(
            bootstrap_servers='localhost:9092',
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8')
        )

        # Snowflake for audit logging
        self.conn = snowflake.connector.connect(
            account   = 'jneusse-po63749',
            user      = 'JEEVAN17',
            password  = 'Sinchanagowda@123',
            warehouse = 'COMPUTE_WH',
            database  = 'RETAIL_OS_DB',
            schema    = 'RAW'
        )

        self.approved = 0
        self.rejected = 0
        print("✅ Decision Engine initialized")

    # ── Business Rules ────────────────────────────────────────
    def apply_rules(self, decision):
        agent = decision.get('agent', '')

        # Rule 1: Demand forecast confidence must be > 0.70
        if agent == 'DemandForecastAgent':
            confidence = decision.get('confidence', 0)
            if confidence < 0.70:
                return False, f"Low confidence: {confidence}"
            if decision.get('predicted_demand', 0) < 0:
                return False, "Negative demand prediction rejected"
            return True, "Demand forecast approved"

        # Rule 2: Reorder qty must be reasonable
        if agent == 'InventoryMonitorAgent':
            reorder_qty = decision.get('reorder_qty', 0)
            if reorder_qty <= 0:
                return False, "Zero reorder quantity rejected"
            if reorder_qty > 10000:
                return False, f"Reorder qty {reorder_qty} exceeds limit"
            return True, "Reorder approved"

        return True, "Approved by default"

    # ── Log to Snowflake ──────────────────────────────────────
    def log_decision(self, decision, approved, reason):
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO RETAIL_OS_DB.RAW.RAW_TRANSACTIONS
                (TRANSACTION_ID, STORE_ID, PRODUCT_ID,
                 QUANTITY_SOLD, UNIT_PRICE, PAYMENT_METHOD)
                SELECT
                    %s, %s, %s, %s, %s, %s
            """, (
                f"DE_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
                decision.get('store_id', 'SYSTEM'),
                decision.get('product_id', 'SYSTEM'),
                1, 0.0,
                f"{'APPROVED' if approved else 'REJECTED'}:{reason}"
            ))
        except Exception as e:
            pass  # Don't block on logging errors

    # ── Main Processing Loop ──────────────────────────────────
    def run(self):
        print("\n" + "=" * 50)
        print("  DECISION ENGINE STARTING")
        print("=" * 50)
        print("Listening to agent topics...")

        for message in self.consumer:
            decision = message.value
            agent    = decision.get('agent', 'Unknown')
            topic    = message.topic

            # Apply business rules
            approved, reason = self.apply_rules(decision)

            if approved:
                self.approved += 1
                decision['decision']        = 'APPROVED'
                decision['reason']          = reason
                decision['approved_at']     = datetime.now().isoformat()

                # Route to action engine
                self.producer.send(
                    'retail.actions.approved',
                    value=decision
                )
                print(f"✅ APPROVED [{agent}] — {reason}")
            else:
                self.rejected += 1
                print(f"❌ REJECTED [{agent}] — {reason}")

        self.producer.flush()
        print(f"\n{'='*50}")
        print(f"  DECISION ENGINE COMPLETED")
        print(f"{'='*50}")
        print(f"  ✅ Approved : {self.approved}")
        print(f"  ❌ Rejected : {self.rejected}")
        print(f"  Total      : {self.approved + self.rejected}")

if __name__ == "__main__":
    engine = DecisionEngine()
    engine.run()
