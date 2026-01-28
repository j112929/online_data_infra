# SDK Package
from sdk.feature_definition import (
    Feature,
    FeatureView,
    Source,
    Sink,
    Window,
    AggregationType,
    WindowType,
    FEATURE_VIEWS
)
from sdk.compiler import compile_feature_view, FlinkSQLCompiler

# LLM Integration (optional - requires openai/anthropic)
try:
    from sdk.llm_integration import (
        LLMClient,
        LLMConfig,
        LLMProvider,
        FeatureGenerator,
        FeatureAdvisor,
        SDKCopilot,
        generate_features,
        get_recommendations
    )
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

__all__ = [
    "Feature",
    "FeatureView", 
    "Source",
    "Sink",
    "Window",
    "AggregationType",
    "WindowType",
    "FEATURE_VIEWS",
    "compile_feature_view",
    "FlinkSQLCompiler",
    "LLM_AVAILABLE",
    # LLM exports (when available)
    "LLMClient",
    "LLMConfig",
    "LLMProvider",
    "FeatureGenerator",
    "FeatureAdvisor",
    "SDKCopilot",
    "generate_features",
    "get_recommendations"
]
