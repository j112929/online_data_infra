from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Feature:
    name: str
    owner: str
    description: str
    ttl_seconds: int

@dataclass
class Source:
    topic: str
    schema: str

class FeatureView:
    def __init__(self, name: str, source: Source, features: List[Feature]):
        self.name = name
        self.source = source
        self.features = features

# Example Definition
user_clicks = FeatureView(
    name="user_click_stats",
    source=Source(topic="user_interactions", schema="avro/user_interaction.avsc"),
    features=[
        Feature(name="click_count_1m", owner="jizhuolin", description="Clicks in last minute", ttl_seconds=3600)
    ]
)
