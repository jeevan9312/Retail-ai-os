# 🛒 Retail-AI-OS — AI-Powered Retail Operating System

An end-to-end, autonomous AI platform that transforms retail operations through intelligent agents, real-time data streaming, and autonomous decision-making — from demand forecasting to logistics dispatch.

---

## 🏗️ Architecture Overview

```
DATA SOURCES
(POS · IoT Sensors · Supplier ERP · Weather APIs · Competitor Prices · Customer Apps)
        │
        ▼
DATA INGESTION LAYER
(FastAPI Services · Batch Upload · Streaming Ingestion)
        │
        ▼
EVENT STREAMING PLATFORM
(Apache Kafka · Event Bus · Stream Processing · Event Routing)
        │
        ▼
DATA LAKE
(MinIO · Raw Retail Data · Transaction Logs · Inventory Snapshots)
        │
        ▼
ENTERPRISE DATA WAREHOUSE
(Snowflake · Sales · Inventory · Customer · Supply Chain Analytics)
        │
        ▼
FEATURE STORE
(Lag Sales · Rolling Demand · Weather Features · Price Elasticity · Festival Signals)
        │
        ▼
AI AGENT ECOSYSTEM  (20 Specialized Agents)
        │
        ▼
AI DECISION ENGINE
(Demand · Pricing · Inventory · Procurement · Logistics)
        │
        ▼
AUTONOMOUS ACTION ENGINE
(Auto Purchase Orders · Dynamic Pricing · Inventory Transfers · Logistics Dispatch)
        │
        ▼
DIGITAL TWIN SIMULATION LAYER
        │
        ▼
REAL-TIME COMMAND CENTER
(Executive · Sales · Inventory · Supply Chain · Marketing Dashboards)
```

---

## 📁 Project Structure

```
Retail-ai-os/
├── agents/                  # 20 specialized AI agents (Base Agent framework)
├── dashboard/               # Real-time command center dashboards
├── data/                    # Raw & processed retail datasets
├── feature_store/           # Feature engineering & storage
├── infra/                   # Infrastructure configs (Kafka, MinIO, Snowflake)
├── logs/                    # System and agent logs
├── retail_dbt/              # dbt models for Snowflake transformations
├── services/
│   └── ingestion/           # FastAPI ingestion services
├── load_to_snowflake.py     # Data loader: MinIO → Snowflake
├── upload_to_minio.py       # Data uploader to MinIO data lake
├── test_snowflake.py        # Snowflake connection tests
└── new.py                   # Utility / scratch scripts
```

---

## 🤖 AI Agent Ecosystem

The platform is powered by **20 specialized AI agents** built on a custom **Base Agent framework**:

| Category | Agents |
|---|---|
| **Demand** | Demand Forecast Agent · Demand Spike Detection Agent |
| **Pricing** | Pricing Optimization Agent · Price Elasticity Agent · Competitor Monitoring Agent |
| **Inventory** | Inventory Monitoring Agent · Warehouse Allocation Agent |
| **Procurement** | Procurement Planning Agent · Supplier Selection Agent |
| **Logistics** | Logistics Optimization Agent · Delivery Prediction Agent |
| **Marketing** | Promotion Strategy Agent · Campaign Analytics Agent |
| **Intelligence** | Market Intelligence Agent · Customer Segmentation Agent |
| **Risk & Safety** | Anomaly Detection Agent · Fraud Detection Agent · Supply Chain Risk Agent |
| **Simulation** | Digital Twin Simulation Agent · Reinforcement Learning Agent |

---

## ⚙️ Tech Stack

| Layer | Technology |
|---|---|
| **Event Streaming** | Apache Kafka |
| **Data Ingestion** | FastAPI |
| **Data Lake / Object Storage** | MinIO |
| **Data Warehouse** | Snowflake |
| **Data Transformation** | dbt (retail_dbt) |
| **AI Agents** | Custom Base Agent Framework (Python) |
| **Language** | Python 3.x |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- Apache Kafka (running locally or via Docker)
- MinIO instance
- Snowflake account
- dbt CLI

### Installation

```bash
git clone https://github.com/jeevan9312/Retail-ai-os.git
cd Retail-ai-os
pip install -r requirements.txt
```

### Configuration

Set up your environment variables:

```bash
# Snowflake
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_USER=your_user
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_DATABASE=RETAIL_DB
SNOWFLAKE_WAREHOUSE=RETAIL_WH

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=your_access_key
MINIO_SECRET_KEY=your_secret_key

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

### Running the Platform

```bash
# Upload raw data to MinIO
python upload_to_minio.py

# Load data from MinIO to Snowflake
python load_to_snowflake.py

# Run dbt transformations
cd retail_dbt
dbt run

# Start ingestion services
cd services/ingestion
uvicorn main:app --reload

# Launch agents
cd agents
python run_agents.py
```

---

## 📊 Dashboards

The Real-Time Command Center (`/dashboard`) provides:

- **Executive Dashboard** — KPIs and business overview
- **Sales Analytics Dashboard** — Revenue, trends, and performance
- **Inventory Monitoring Dashboard** — Stock levels and alerts
- **Demand Forecast Dashboard** — Predicted vs actual demand
- **Supply Chain Optimization Dashboard** — End-to-end logistics view
- **Supplier Analytics Dashboard** — Vendor performance metrics
- **Marketing Performance Dashboard** — Campaign and promotion ROI
- **Real-Time Alerts Dashboard** — Anomalies and critical events

---

## 🧪 Testing

```bash
# Test Snowflake connectivity
python test_snowflake.py
```

---

## 🗺️ Roadmap

- [ ] Add REST API layer for external integrations
- [ ] Containerize with Docker Compose (Kafka + MinIO + App)
- [ ] Add agent observability & tracing
- [ ] Build reinforcement learning feedback loop
- [ ] Add CI/CD pipeline with GitHub Actions

---

## 🤝 Contributing

Contributions are welcome! Please open an issue or submit a pull request.

---

## 📄 License

This project is licensed under the MIT License.

---

## 👤 Author

**Jeevan** — [@jeevan9312](https://github.com/jeevan9312)
