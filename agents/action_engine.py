import sys
sys.path.insert(0, '.')
import json
import os
from kafka import KafkaConsumer, KafkaProducer
from datetime import datetime
from config import SNOWFLAKE_CONFIG, KAFKA_CONFIG
import snowflake.connector

class ActionEngine:
    def __init__(self):
        # Read approved decisions from Decision Engine
        self.consumer = KafkaConsumer(
            'retail.actions.approved',
            bootstrap_servers=KAFKA_CONFIG['bootstrap_servers'],
            value_deserializer=lambda v: json.loads(v.decode('utf-8')),
            auto_offset_reset='earliest',
            consumer_timeout_ms=5000,
            group_id='action_engine'
        )

        self.producer = KafkaProducer(
            bootstrap_servers=KAFKA_CONFIG['bootstrap_servers'],
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8')
        )

        self.conn = snowflake.connector.connect(**SNOWFLAKE_CONFIG)

        # Action counters
        self.purchase_orders = []
        self.price_updates   = []
        self.alerts          = []

        print("✅ Action Engine initialized")

    # ── Action 1: Create Purchase Order ──────────────────────
    def create_purchase_order(self, decision):
        po = {
            'po_id':        f"PO-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            'product_id':   decision.get('product_id'),
            'warehouse_id': decision.get('warehouse_id'),
            'quantity':     decision.get('reorder_qty', 0),
            'status':       'CREATED',
            'priority':     decision.get('priority', 'MEDIUM'),
            'created_at':   datetime.now().isoformat(),
            'action':       'PURCHASE_ORDER_CREATED'
        }
        self.purchase_orders.append(po)

        # Publish PO created event
        self.producer.send('retail.actions.purchase_orders', value=po)
        print(f"🛒 PO Created: {po['po_id']} — Product {po['product_id']} x {po['quantity']} units")
        return po

    # ── Action 2: Update Price ────────────────────────────────
    def update_price(self, decision):
        update = {
            'product_id':       decision.get('product_id'),
            'store_id':         decision.get('store_id'),
            'predicted_demand': decision.get('predicted_demand'),
            'price_action':     'HOLD',  # Hold price when demand is normal
            'updated_at':       datetime.now().isoformat(),
            'action':           'PRICE_REVIEWED'
        }
        # Simple rule: if predicted demand is high, suggest price increase
        if decision.get('predicted_demand', 0) > 10:
            update['price_action'] = 'INCREASE_5PCT'
        elif decision.get('predicted_demand', 0) < 2:
            update['price_action'] = 'DECREASE_5PCT'

        self.price_updates.append(update)
        self.producer.send('retail.actions.pricing', value=update)
        print(f"💰 Price Update: Product {update['product_id']} → {update['price_action']}")
        return update

    # ── Action 3: Send Alert ──────────────────────────────────
    def send_alert(self, decision):
        alert = {
            'alert_id':   f"ALT-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            'type':       'STOCKOUT_RISK' if decision.get('stock_status') == 'OUT_OF_STOCK' else 'REORDER_NEEDED',
            'product_id': decision.get('product_id'),
            'message':    f"Product {decision.get('product_id')} — {decision.get('stock_status')} at warehouse {decision.get('warehouse_id')}",
            'priority':   decision.get('priority', 'MEDIUM'),
            'created_at': datetime.now().isoformat()
        }
        self.alerts.append(alert)
        self.producer.send('retail.actions.alerts', value=alert)
        print(f"🚨 Alert: {alert['type']} — {alert['message']}")
        return alert

    # ── Route decisions to correct action ────────────────────
    def process_decision(self, decision):
        agent = decision.get('agent', '')

        if agent == 'InventoryMonitorAgent':
            self.create_purchase_order(decision)
            self.send_alert(decision)

        elif agent == 'DemandForecastAgent':
            self.update_price(decision)

    # ── Save summary to file ──────────────────────────────────
    def save_summary(self):
        summary = {
            'timestamp':      datetime.now().isoformat(),
            'purchase_orders': self.purchase_orders,
            'price_updates':   self.price_updates,
            'alerts':          self.alerts,
        }
        with open('action_summary.json', 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        print(f"\n📄 Summary saved to action_summary.json")

    # ── Main Loop ─────────────────────────────────────────────
    def run(self):
        print("\n" + "=" * 50)
        print("  AUTONOMOUS ACTION ENGINE STARTING")
        print("=" * 50)
        print("Waiting for approved decisions...")

        for message in self.consumer:
            decision = message.value
            self.process_decision(decision)

        self.producer.flush()
        self.save_summary()

        print(f"\n{'='*50}")
        print(f"  ACTION ENGINE COMPLETED")
        print(f"{'='*50}")
        print(f"  🛒 Purchase Orders : {len(self.purchase_orders)}")
        print(f"  💰 Price Updates   : {len(self.price_updates)}")
        print(f"  🚨 Alerts Sent     : {len(self.alerts)}")

if __name__ == "__main__":
    engine = ActionEngine()
    engine.run()