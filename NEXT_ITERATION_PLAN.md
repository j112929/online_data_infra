# Next Iteration Roadmap (Feature Platform v2)

Based on the current MVP, here are the recommended steps to evolve the platform into a production-grade system.

## 1. Core Data Path Enhancements (Priority: High)
Currently, `processing/feature_job.py` prints to console. We need to close the loop.

*   **Implement Real Redis Sink**:
    *   Replace the `print` connector with a proper Redis sink (using `flink-connector-redis` or a custom `RichSinkFunction` in PyFlink).
    *   **Goal**: Data flows automagically from Kafka -> Flink -> Redis.
*   **Offline Store Integration (Iceberg/Hudi)**:
    *   Feature Stores need an "Offline Store" for training data generation.
    *   **Action**: Add MinIO (S3 compatible) to Docker Compose. Configure Flink to sink raw events to Iceberg for historical queries.

## 2. SDK Operationalization (Priority: High)
The `sdk/feature_definition.py` is currently a passive data structure.

*   **"Compiler" for the SDK**:
    *   Build a transpiler that takes the Python `FeatureView` definition and **generates** the Flink SQL job automatically.
    *   **Goal**: Users only write Python; the platform deploys the SQL.
*   **CI/CD Integration**:
    *   CLI tool (e.g., `infra apply`) that registers schemas to the Registry and submits Flink jobs.

## 3. Data Quality & Observability
*   **Data Contracts**: Enforce quality at the ingestion layer.
*   **Drift Detection**: Calculate statistical distribution of features in Flink (e.g., mean/std-dev) and alert if live data drifts from training data.
*   **Backfill Orchestration**:
    *   Implement an Airflow DAG that triggers a batch Flink job to compute historical features and load them into the Offline Store.

## 4. Serving Optimization
*   **Batch Inference API**: `POST /features/batch` to fetch features for 100+ users in one request (critical for ranking models).
*   **On-Demand Features**: Support transformation logic in the serving layer (e.g., `age = now() - dob`) for real-time context that doesn't need Flink state.

## 5. Recommended Immediate Next Step
**Implement the Real Redis Sink in Flink**. This completes the "Real-Time" path effectively.

### Proposed Task: Connect Flink to Redis
1.  Add `flink-connector-redis` dependency.
2.  Update `feature_job.py` to write to Redis using `HMSET` (Hash Map) structure.
3.  Verify the data appears in Redis for the Serving API to consume.
