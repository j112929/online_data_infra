from fastapi import FastAPI, HTTPException
import redis
import os
import time
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# Setup Tracing
trace.set_tracer_provider(TracerProvider())
otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True)
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(otlp_exporter))

app = FastAPI(title="Feature Serving API")
FastAPIInstrumentor.instrument_app(app)

# Redis Client
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

tracer = trace.get_tracer(__name__)

@app.get("/features/{user_id}")
async def get_features(user_id: str):
    with tracer.start_as_current_span("fetch_from_redis"):
        # Simulate cost model tracking
        start_time = time.time()
        
        # In a real scenario, Flink would write to keys like "user:{id}:click_count"
        # Since our demo Flink job 'prints' (or if we had a Redis Sink), we assume data is there.
        # We will mock a fallback if missing.
        key = f"user:{user_id}:click_count"
        value = r.get(key)
        
        duration = time.time() - start_time
        # Log metric for Cost Model (CPU/Time)
        # In a real system, publish this to Prometheus/CloudWatch
        print(f"CostModel: Read feature='{key}' duration={duration:.4f}s")

    if value is None:
        return {"user_id": user_id, "click_count": 0, "source": "default"}
    
    return {"user_id": user_id, "click_count": int(value), "source": "feature_store"}

@app.get("/health")
def health():
    return {"status": "ok"}
