# Unified Real-Time Feature Platform

A production-ready reference architecture for real-time feature engineering, combining streaming processing with low-latency serving.

## 🏗 Architecture
**Data Flow**: 
`Kafka (Ingestion)` → `Flink (Stateful Processing)` → `Redis (Feature Store)` → `FastAPI (Serving)`

**Observability**:
`Jaeger (Distributed Tracing)` + `Prometheus (Metrics)`

### Key Features
| Feature | Implementation Detail |
| :--- | :--- |
| **Exactly-once** | Flink Checkpointing + Transactional Connectors + Idempotent Redis Writes. |
| **Backfill** | Unified Source API (supports rewinding offsets or swapping to S3/Iceberg sources). |
| **Schema Evolution** | Confluent Schema Registry (Avro) ensures data compatibility. |
| **Latency Monitor** | End-to-End Tracing (OpenTelemetry) from API request to backend fetch. |
| **Cost Model** | Serving layer tracks compute/network latency per feature. |

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
uvicorn serving.app:app --reload
```

### 4. Verify & Explore
*   **Get Features**: 
    ```bash
    curl http://localhost:8000/features/1
    ```
    *Response should show `"source": "feature_store"` and a non-zero count.*

*   **Dashboards**:
    *   **Jaeger (Traces)**: [http://localhost:16686](http://localhost:16686)
    *   **Grafana**: [http://localhost:3000](http://localhost:3000)
    *   **Schema Registry**: [http://localhost:8082](http://localhost:8082)

---

## 📂 Project Structure
```
online_data_infra/
├── ingestion/          # Python Kafka Producers (Avgro + Schema Registry)
├── processing/         # PyFlink Jobs (SQL + DataStream Hybrid API)
│   ├── feature_job.py  # Main Pipeline: Aggregation -> Redis Sink
│   └── lib/            # Dependency JARs
├── feature_store/      # Connector logic (Abstracted)
├── serving/            # FastAPI + OpenTelemetry + Cost Tracking
├── monitoring/         # Prometheus/Grafana/Jaeger Configs
└── deployment/         # Docker Compose Environment
```

## 🛠 Tech Stack
*   **Streaming**: Apache Flink 1.18 (PyFlink)
*   **Messaging**: Kafka + Confluent Schema Registry
*   **Storage**: Redis (Online Store)
*   **Serving**: FastAPI
*   **Observability**: OpenTelemetry, Jaeger, Prometheus

## 📝 Next Steps
See [NEXT_ITERATION_PLAN.md](NEXT_ITERATION_PLAN.md) for the roadmap towards v2 (Iceberg integration, SDK Compiler, etc.).
