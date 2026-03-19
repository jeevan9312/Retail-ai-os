from abc import ABC, abstractmethod
from kafka import KafkaProducer
import json
import snowflake.connector
from datetime import datetime

class BaseAgent(ABC):
    def __init__(self, agent_name, input_topic, output_topic):
        self.agent_name   = agent_name
        self.input_topic  = input_topic
        self.output_topic = output_topic

        self.producer = KafkaProducer(
            bootstrap_servers='localhost:9092',
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8')
        )

        self.conn = snowflake.connector.connect(
            account   = 'jneusse-po63749',
            user      = 'JEEVAN17',
            password  = 'Sinchanagowda@123',
            warehouse = 'COMPUTE_WH',
            database  = 'RETAIL_OS_DB',
            schema    = 'MARTS'
        )
        print(f"✅ {self.agent_name} initialized")

    def publish_decision(self, decision: dict):
        decision['agent']     = self.agent_name
        decision['timestamp'] = datetime.now().isoformat()
        self.producer.send(self.output_topic, value=decision)
        self.producer.flush()
        print(f"📤 Published: {decision}")

    def query_snowflake(self, sql: str):
        cursor  = self.conn.cursor()
        cursor.execute(sql)
        columns = [col[0] for col in cursor.description]
        rows    = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]

    @abstractmethod
    def run(self):
        pass