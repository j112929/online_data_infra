# Unified Real-Time Feature Platform Implementation Plan

## Architecture Overview
**Pipeline**: Kafka → Flink → Feature Store → Online Serving → Trace

## Key Requirements & Implementation Strategy

### 1. Exactly-Once Processing
- **Mechanism**: Flink Checkpointing + Two-Phase Commit (2PC) sinks.
- **Kafka**: Use `FlinkKafkaConsumer` with `semantic.exactly-once`.
- **State Backend**: RocksDB for large state management.
- **Sink**: Idempotent writes to Feature Store (e.g., Redis/Cassandra) or transactional sinks if supported.

### 2. Backfill Capability (回填能力)
- **Hybrid Source**: Unified API to read from both Historical (e.g., S3/HDFS/Iceberg) and Real-time (Kafka) sources.
- **Kappa Architecture**: Treat history as a separate stream or effectively "rewind" offsets if data retention allows.
- **Version Control**: Feature definitions versioned in code to ensure backfills use the correct logic.

### 3. Schema Evolution
- **Registry**: Use a Schema Registry (e.g., Confluent Schema Registry or a lightweight internal one).
- **Protobuf/Avro**: Strong typing for messages.
- **Migration Strategy**: 
    - Forward/backward compatibility checks.
    - Flink state schema evolution (using POJO or Avro/Protobuf serialization to allow state migration).

### 4. Latency Monitoring (延迟监控)
- **Metrics**: 
    - Event Time vs Processing Time lag.
    - End-to-end latency (Ingestion to Serving).
- **Tracing**: OpenTelemetry integration. Propagate `trace_id` from Kafka headers -> Flink -> Feature Store -> Serving.

### 5. Cost Model
- **Resource Utilization**: Track CPU/Memory per feature pipeline.
- **Storage Cost**: Volumetric tracking of feature store usage (TTL policies).
- **Throughput**: Events per second (EPS) processing cost.

## Project Structure
```
online_data_infra/
├── ingestion/          # Kafka Producers, Schema Registry interactions
├── processing/         # Flink Jobs (SQL/DataStream API)
├── feature_store/      # Storage connectors (Redis), Schema definitions
├── serving/            # HTTP/gRPC Serving Layer (FastAPI/Go)
├── monitoring/         # Prometheus/Grafana/OpenTelemetry configs
├── deployment/         # Docker Compose, K8s manifests
└── sdk/                # Python/Java SDK for defining features
```

## Step-by-Step Execution
1. **Infrastructure Setup**: Docker Compose for Kafka, Zookeeper, Flink Cluster, Redis (Feature Store), and Prometheus/Grafana.
2. **Ingestion Layer**: Define Avro schemas and a mock data generator (Producer).
3. **Processing Layer**: Implement Flink job with Checkpointing enabled.
4. **Feature Store**: Implement Redis sink with idempotent write logic.
5. **Serving Layer**: Create a FastAPI service to fetch features.
6. **Backfill & Evolution**: Demonstrate schema update workflow and historical data processing.
