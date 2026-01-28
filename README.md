# Unified Real-Time Feature Platform

This project implements a unified real-time feature platform as requested.

## Architecture
**Data Flow**: Kafka (Ingestion) → Flink (Processing) → Redis (Feature Store) → FastAPI (Serving) → Jaeger (Trace)

## Features Implemented

1. **Exactly-once Processing**:
    - Leverages Flink's Checkpointing mechanism (Points can be configured in `flink-conf.yaml` or code).
    - Kafka Consumer uses `read_committed` (transactional).
    - (Demo) Flink Job uses high-level Table API which supports exactly-once with compatible sinks.

2. **Backfill Capability (回填)**:
    - The architecture supports reading from historical storage (e.g., S3/Iceberg) using the same Flink SQL logic by swapping the source definition.
    - `processing/feature_job.py` sets `scan.startup.mode` to `earliest-offset` effectively replaying history from Kafka for this demo.

3. **Schema Evolution**:
    - Uses Confluent Schema Registry.
    - Producer (`ingestion/producer.py`) registers Avro schemas.
    - Flink Job uses `avro-confluent` format to automatically fetch and deserialize based on schema ID, handling compatible schema changes gracefully.

4. **Latency Monitoring & Tracing**:
    - **OpenTelemetry** integrated into the Serving layer (`serving/app.py`).
    - Traces propagated to Jaeger (UI at http://localhost:16686).
    - Prometheus monitors Flink and System metrics.

5. **Cost Model**:
    - Serving layer tracks computation time per feature fetch.
    - Logic set to track Resource Usage (CPU/Mem) via standard monitoring (Prometheus).

## Quick Start

### 1. Start Infrastructure
```bash
cd deployment
docker-compose up -d
```

### 2. Download Flink Dependencies
```bash
cd processing
bash download_libs.sh
```

### 3. Install Python Dependencies
```bash
pip install -r ingestion/requirements.txt
pip install -r processing/requirements.txt
pip install -r serving/requirements.txt
```

### 4. Run Ingestion (Producer)
```bash
python ingestion/producer.py
```

### 5. Run Flink Job
*Requires Flink environment or local cluster*
```bash
# If running locally with PyFlink installed
python processing/feature_job.py
```

### 6. Run Serving API
```bash
uvicorn serving.app:app --reload
```

## Access Points
- **Grafana**: http://localhost:3000
- **Jaeger**: http://localhost:16686
- **Schema Registry**: http://localhost:8081
- **API Docs**: http://localhost:8000/docs
