from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import redis
import os
import time
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
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

# Prometheus Metrics
FEATURE_REQUESTS = Counter(
    'feature_requests_total', 
    'Total feature requests',
    ['endpoint', 'source']
)
FEATURE_LATENCY = Histogram(
    'feature_latency_seconds',
    'Feature fetch latency in seconds',
    ['endpoint'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)
BATCH_SIZE = Histogram(
    'batch_request_size',
    'Number of users per batch request',
    buckets=[1, 5, 10, 25, 50, 100, 250, 500]
)

app = FastAPI(
    title="Feature Serving API",
    description="Real-time feature serving for ML models with LLM-powered feature engineering",
    version="1.0.0"
)

# Mount LLM API routes
try:
    from serving.llm_api import app as llm_app
    app.mount("/api", llm_app)
except ImportError:
    pass  # LLM dependencies not installed

FastAPIInstrumentor.instrument_app(app)

# Redis Client
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

tracer = trace.get_tracer(__name__)

# Request/Response Models
class BatchRequest(BaseModel):
    user_ids: List[str]
    features: Optional[List[str]] = None  # Optional: specific features to fetch

class FeatureResponse(BaseModel):
    user_id: str
    click_count: int
    source: str

class BatchResponse(BaseModel):
    results: List[FeatureResponse]
    latency_ms: float
    batch_size: int


def fetch_user_features(user_id: str) -> Dict[str, Any]:
    """Fetch features for a single user from Redis."""
    key = f"user:{user_id}:click_count"
    value = r.get(key)
    
    if value is None:
        return {"user_id": user_id, "click_count": 0, "source": "default"}
    return {"user_id": user_id, "click_count": int(value), "source": "feature_store"}


@app.get("/features/{user_id}", response_model=FeatureResponse)
async def get_features(user_id: str):
    """Get features for a single user."""
    with tracer.start_as_current_span("fetch_single_user"):
        start_time = time.time()
        
        result = fetch_user_features(user_id)
        
        duration = time.time() - start_time
        
        # Record metrics
        FEATURE_REQUESTS.labels(endpoint="single", source=result["source"]).inc()
        FEATURE_LATENCY.labels(endpoint="single").observe(duration)
        
    return result


@app.post("/features/batch", response_model=BatchResponse)
async def get_features_batch(request: BatchRequest):
    """
    Get features for multiple users in a single request.
    
    This is optimized for batch inference scenarios where you need
    features for many users at once (e.g., ranking models).
    
    Example:
    ```json
    {
        "user_ids": ["1", "2", "3", "4", "5"]
    }
    ```
    """
    with tracer.start_as_current_span("fetch_batch_users") as span:
        start_time = time.time()
        batch_size = len(request.user_ids)
        
        span.set_attribute("batch_size", batch_size)
        
        # Use Redis pipeline for efficient batch fetching
        with tracer.start_as_current_span("redis_pipeline"):
            pipe = r.pipeline()
            for user_id in request.user_ids:
                pipe.get(f"user:{user_id}:click_count")
            values = pipe.execute()
        
        # Build results
        results = []
        feature_store_count = 0
        default_count = 0
        
        for user_id, value in zip(request.user_ids, values):
            if value is None:
                results.append({
                    "user_id": user_id,
                    "click_count": 0,
                    "source": "default"
                })
                default_count += 1
            else:
                results.append({
                    "user_id": user_id,
                    "click_count": int(value),
                    "source": "feature_store"
                })
                feature_store_count += 1
        
        duration = time.time() - start_time
        latency_ms = duration * 1000
        
        # Record metrics
        FEATURE_REQUESTS.labels(endpoint="batch", source="feature_store").inc(feature_store_count)
        FEATURE_REQUESTS.labels(endpoint="batch", source="default").inc(default_count)
        FEATURE_LATENCY.labels(endpoint="batch").observe(duration)
        BATCH_SIZE.observe(batch_size)
        
        span.set_attribute("latency_ms", latency_ms)
        span.set_attribute("feature_store_hits", feature_store_count)
        span.set_attribute("default_hits", default_count)
    
    return BatchResponse(
        results=results,
        latency_ms=round(latency_ms, 2),
        batch_size=batch_size
    )


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/health")
def health():
    """Health check endpoint."""
    try:
        r.ping()
        return {"status": "ok", "redis": "connected"}
    except redis.ConnectionError:
        return {"status": "degraded", "redis": "disconnected"}
