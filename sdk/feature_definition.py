"""
Feature Platform SDK

This SDK provides a declarative way to define features.
The SDK Compiler can generate Flink SQL jobs from these definitions.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Literal, Dict, Any
from enum import Enum


class AggregationType(Enum):
    """Supported aggregation types."""
    COUNT = "COUNT"
    SUM = "SUM"
    AVG = "AVG"
    MIN = "MIN"
    MAX = "MAX"
    COUNT_DISTINCT = "COUNT_DISTINCT"


class WindowType(Enum):
    """Supported window types."""
    TUMBLE = "TUMBLE"
    HOP = "HOP"
    SESSION = "SESSION"


@dataclass
class Window:
    """Window configuration for feature aggregation."""
    type: WindowType = WindowType.TUMBLE
    size_minutes: int = 1
    slide_minutes: Optional[int] = None  # For HOP windows


@dataclass
class Feature:
    """A single feature definition."""
    name: str
    description: str
    aggregation: AggregationType
    source_field: str
    filter_condition: Optional[str] = None  # e.g., "action_type = 'click'"
    owner: str = "platform"
    ttl_seconds: int = 3600


@dataclass
class Source:
    """Kafka source configuration."""
    topic: str
    bootstrap_servers: str = "localhost:9092"
    schema_registry_url: str = "http://localhost:8082"
    group_id: str = "feature_group"
    
    # Schema fields (inferred or explicit)
    fields: Dict[str, str] = field(default_factory=dict)  # field_name -> type
    timestamp_field: str = "timestamp"
    key_field: str = "user_id"


@dataclass
class Sink:
    """Feature store sink configuration."""
    type: Literal["redis", "print"] = "redis"
    host: str = "localhost"
    port: int = 6379
    key_template: str = "user:{key_field}:{feature_name}"


@dataclass
class FeatureView:
    """
    A FeatureView represents a group of features computed from a single source.
    
    Example:
    ```python
    user_clicks = FeatureView(
        name="user_click_stats",
        source=Source(topic="user_interactions"),
        features=[
            Feature(
                name="click_count_1m",
                description="Click count in last minute",
                aggregation=AggregationType.COUNT,
                source_field="*",
                filter_condition="action_type = 'click'"
            )
        ],
        window=Window(type=WindowType.TUMBLE, size_minutes=1),
        entity_key="user_id"
    )
    ```
    """
    name: str
    source: Source
    features: List[Feature]
    window: Window = field(default_factory=Window)
    entity_key: str = "user_id"
    sink: Sink = field(default_factory=Sink)


# ============================================================
# Example Feature Definitions
# ============================================================

# Source definition with explicit fields
interactions_source = Source(
    topic="user_interactions",
    bootstrap_servers="localhost:9092",
    schema_registry_url="http://localhost:8082",
    fields={
        "user_id": "STRING",
        "item_id": "STRING",
        "action_type": "STRING",
        "timestamp": "BIGINT",
        "context": "STRING"
    },
    timestamp_field="timestamp",
    key_field="user_id"
)

# Feature View 1: Click Stats
user_click_stats = FeatureView(
    name="user_click_stats",
    source=interactions_source,
    features=[
        Feature(
            name="click_count_1m",
            description="Total clicks in the last minute",
            aggregation=AggregationType.COUNT,
            source_field="*",
            filter_condition="action_type = 'click'",
            owner="ml-team",
            ttl_seconds=3600
        ),
        Feature(
            name="view_count_1m",
            description="Total views in the last minute",
            aggregation=AggregationType.COUNT,
            source_field="*",
            filter_condition="action_type = 'view'",
            owner="ml-team",
            ttl_seconds=3600
        ),
    ],
    window=Window(type=WindowType.TUMBLE, size_minutes=1),
    entity_key="user_id"
)

# Feature View 2: Purchase Stats
user_purchase_stats = FeatureView(
    name="user_purchase_stats",
    source=interactions_source,
    features=[
        Feature(
            name="purchase_count_5m",
            description="Total purchases in the last 5 minutes",
            aggregation=AggregationType.COUNT,
            source_field="*",
            filter_condition="action_type = 'purchase'",
            owner="ml-team",
            ttl_seconds=7200
        ),
    ],
    window=Window(type=WindowType.TUMBLE, size_minutes=5),
    entity_key="user_id"
)


# Registry of all feature views
FEATURE_VIEWS = [
    user_click_stats,
    user_purchase_stats
]
