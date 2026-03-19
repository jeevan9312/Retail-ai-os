from kafka import KafkaProducer
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Connect to Kafka
producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def publish_to_kafka(topic: str, event: dict):
    """Send one event to a Kafka topic"""
    producer.send(topic, value=event)
    producer.flush()
    print(f"Published to {topic}: {list(event.keys())}")

if __name__ == "__main__":
    # Quick test — send one transaction event
    test_event = {
        "transaction_id": "T001",
        "store_id":        "S01",
        "sku_id":          "SKU123",
        "quantity":        2,
        "price":           29.99,
        "timestamp":       "2024-01-15T10:30:00"
    }
    publish_to_kafka("retail.pos.transactions", test_event)
    print("Test complete!")