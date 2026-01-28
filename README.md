# Unified Real-Time Feature Platform

A production-ready reference architecture for real-time feature engineering, combining streaming processing with low-latency serving.

## 🏗 Architecture
**Data Flow**: 
`Kafka (Ingestion)` → `Flink (Stateful Processing)` → `Redis (Feature Store)` → `FastAPI (Serving)`

**Observability**:
`Jaeger (Distributed Tracing)` + `Prometheus (Metrics)` + `Grafana (Dashboards)`

### Key Features
| Feature | Implementation Detail |
| :--- | :--- |
| **Exactly-once** | Flink Checkpointing + Transactional Connectors + Idempotent Redis Writes. |
| **Backfill** | Unified Source API (supports rewinding offsets or swapping to S3/Iceberg sources). |
| **Schema Evolution** | Confluent Schema Registry (Avro) ensures data compatibility. |
| **Latency Monitor** | End-to-End Tracing (OpenTelemetry) + Prometheus Metrics + Grafana Dashboards. |
| **Cost Model** | Serving layer tracks compute/network latency per feature with Prometheus histograms. |
| **Batch Inference** | High-performance batch API using Redis pipelines. |
| **SDK Compiler** | Auto-generate Flink SQL jobs from Python feature definitions. |
| **🤖 LLM Copilot** | Natural language feature generation, recommendations, and interactive assistant. |

---

## 🚀 Quick Start

### Prerequisites
*   **Docker & Docker Compose**
*   **Java 11** (Required for PyFlink Local Execution)
*   **Python 3.8+**

### 1. Start Infrastructure
Launch Kafka, Zookeeper, Redis, Schema Registry, and Monitoring stack.
```bash
cd deployment
docker-compose up -d
```

### 2. Setup Processing Engine (PyFlink)
PyFlink requires specific JARs to interact with Kafka and Schema Registry.
```bash
cd processing
# 1. Install Python Deps
pip install -r requirements.txt

# 2. Download Java Dependencies
bash download_libs.sh
```

### 3. Run the Pipeline

#### Terminal 1: Real-Time Feature Engine (Flink)
*Note: Set JAVA_HOME to your Java 11 installation.*
```bash
# macOS Example
export JAVA_HOME="/opt/homebrew/opt/openjdk@11/libexec/openjdk.jdk/Contents/Home"
export PATH="$JAVA_HOME/bin:$PATH"

python processing/feature_job.py
```
*Expected Output: "Submitting Job..." and stays running.*

#### Terminal 2: Data Generator (Producer)
Simulate user behavior (Clicks/Views).
```bash
python ingestion/producer.py
```

#### Terminal 3: Feature Serving API
Start the HTTP Service.
```bash
python -m uvicorn serving.app:app --host 0.0.0.0 --port 8000
```

### 4. Verify & Explore

#### Single User Feature Fetch
```bash
curl http://localhost:8000/features/1
# {"user_id":"1","click_count":5,"source":"feature_store"}
```

#### Batch Feature Fetch (NEW!)
Optimized for ranking models - fetch features for many users in one request.
```bash
curl -X POST http://localhost:8000/features/batch \
  -H "Content-Type: application/json" \
  -d '{"user_ids": ["1", "2", "3", "4", "5"]}'
# {"results":[...], "latency_ms": 1.23, "batch_size": 5}
```

#### Prometheus Metrics
```bash
curl http://localhost:8000/metrics
```

---

## 📊 Grafana Dashboards

A pre-built dashboard is available at `monitoring/grafana-dashboard.json`.

### Import Dashboard
1. Open Grafana: http://localhost:3000 (admin/admin)
2. Go to **Dashboards** → **Import**
3. Upload `monitoring/grafana-dashboard.json`
4. Select Prometheus as the data source

### Dashboard Panels
- **Feature Latency (p50/p95/p99)** - Time series of serving latency
- **Request Rate by Endpoint** - Single vs Batch requests
- **Feature Store Hit Rate** - Percentage of requests served from Redis vs defaults
- **Batch Request Size Distribution** - Histogram of batch sizes

---

## 🛠 SDK Compiler

Define features in Python, auto-generate Flink SQL jobs.

### List Available Features
```bash
python -m sdk.compiler --list
# Available FeatureViews:
#   - user_click_stats
#       • click_count_1m: Total clicks in the last minute
#       • view_count_1m: Total views in the last minute
#   - user_purchase_stats
#       • purchase_count_5m: Total purchases in the last 5 minutes
```

### Generate Flink Job
```bash
python -m sdk.compiler -f user_click_stats -o processing/generated_user_click_stats.py
```

### Define New Features
Edit `sdk/feature_definition.py`:
```python
from sdk import FeatureView, Feature, Source, Window, AggregationType, WindowType

my_feature = FeatureView(
    name="my_feature_view",
    source=Source(topic="my_topic"),
    features=[
        Feature(
            name="my_count",
            description="Count of events",
            aggregation=AggregationType.COUNT,
            source_field="*"
        )
    ],
    window=Window(type=WindowType.TUMBLE, size_minutes=5),
    entity_key="user_id"
)
```

---

## 🤖 LLM Copilot (AI-Powered Feature Engineering)

The platform includes an LLM-powered assistant for feature engineering.

### Setup
```bash
# Install LLM dependencies
pip install openai anthropic

# Set API key
export OPENAI_API_KEY="sk-..."
# OR
export ANTHROPIC_API_KEY="..."
```

### CLI: Interactive Copilot
Chat with the SDK Copilot for help with feature definitions:
```bash
python sdk/cli.py chat
# 🤖 Feature Platform SDK Copilot
# Ask me anything about feature engineering!
# 
# 🧑 You: How do I create a feature that counts purchases per hour?
# 🤖 Copilot: Here's how you can create a purchase count feature...
```

### CLI: Generate Features from Natural Language
```bash
python sdk/cli.py generate
# 📝 Describe your features:
# > I want to track clicks and views per user in 5-minute windows
# 
# 📦 Generated Code:
# from sdk import FeatureView, Feature, ...
```

### CLI: Get Feature Recommendations
```bash
python sdk/cli.py recommend
# 🎯 Use Case: CTR prediction for e-commerce
# 
# 💡 Feature Recommendations:
# 1. click_through_rate_1h - Recent engagement signal
# 2. purchase_frequency_7d - Long-term conversion indicator
# ...
```

### REST API Endpoints
The LLM features are also available via REST API:

| Endpoint | Method | Description |
|:---------|:-------|:------------|
| `/api/llm/generate` | POST | Generate feature code from description |
| `/api/llm/recommend` | POST | Get AI-powered feature recommendations |
| `/api/llm/chat` | POST | Chat with SDK Copilot |
| `/api/llm/health` | GET | Check LLM API availability |

Example API call:
```bash
curl -X POST http://localhost:8000/api/llm/generate \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Count user clicks and purchases in the last 10 minutes",
    "source_schema": {
      "user_id": "STRING",
      "action_type": "STRING",
      "timestamp": "BIGINT"
    }
  }'
```

---

## 📂 Project Structure
```
online_data_infra/
├── ingestion/              # Kafka Producers (Avro + Schema Registry)
├── processing/             # PyFlink Jobs (SQL + DataStream Hybrid API)
│   ├── feature_job.py      # Main Pipeline: Aggregation -> Redis Sink
│   ├── generated_*.py      # Auto-generated jobs from SDK
│   └── lib/                # Dependency JARs
├── serving/                # FastAPI + OpenTelemetry + Prometheus Metrics
│   ├── app.py              # Single + Batch endpoints
│   └── llm_api.py          # LLM-powered feature engineering API
├── sdk/                    # Feature Definition SDK
│   ├── feature_definition.py  # Define features here
│   ├── compiler.py         # Transpiles Python → Flink SQL
│   ├── llm_integration.py  # LLM client and agents
│   └── cli.py              # Interactive CLI tool
├── monitoring/             # Grafana dashboards, Prometheus configs
│   └── grafana-dashboard.json
└── deployment/             # Docker Compose Environment
```

## 🔗 Access Points
| Service | URL |
|:--------|:----|
| **Feature API** | http://localhost:8000 |
| **API Docs (Swagger)** | http://localhost:8000/docs |
| **LLM API Docs** | http://localhost:8000/api/docs |
| **Prometheus Metrics** | http://localhost:8000/metrics |
| **Grafana** | http://localhost:3000 |
| **Jaeger (Traces)** | http://localhost:16686 |
| **Schema Registry** | http://localhost:8082 |
| **Flink Dashboard** | http://localhost:8081 |

## 🛠 Tech Stack
*   **Streaming**: Apache Flink 1.18 (PyFlink)
*   **Messaging**: Kafka + Confluent Schema Registry
*   **Storage**: Redis (Online Store)
*   **Serving**: FastAPI + Prometheus + OpenTelemetry
*   **Observability**: Jaeger, Prometheus, Grafana
*   **AI/LLM**: OpenAI GPT-4o / Anthropic Claude 3

## 📝 Next Steps
See [NEXT_ITERATION_PLAN.md](NEXT_ITERATION_PLAN.md) for the roadmap towards v2.

