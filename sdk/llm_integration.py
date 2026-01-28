"""
LLM Integration Module for Feature Platform

Provides:
1. Natural Language to Feature Definition conversion
2. Feature Advisor - recommendations based on patterns
3. SDK Copilot - interactive feature engineering assistant
"""
import os
import json
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

# Support both OpenAI and Anthropic
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


@dataclass
class LLMConfig:
    """Configuration for LLM integration."""
    provider: LLMProvider = LLMProvider.OPENAI
    api_key: Optional[str] = None
    model: str = "gpt-4o"  # or "claude-3-sonnet-20240229"
    temperature: float = 0.7
    max_tokens: int = 2000


# System prompts for different use cases
FEATURE_DEFINITION_PROMPT = """You are an expert in real-time feature engineering for ML systems.
Your task is to convert natural language feature descriptions into Python code using the Feature Platform SDK.

The SDK provides these components:
- FeatureView: A group of features computed from a single source
- Feature: A single feature with aggregation logic
- Source: Kafka source configuration
- Window: Time window for aggregation (TUMBLE or HOP)
- AggregationType: COUNT, SUM, AVG, MIN, MAX, COUNT_DISTINCT

Example SDK code:
```python
from sdk import FeatureView, Feature, Source, Window, AggregationType, WindowType

source = Source(
    topic="user_interactions",
    fields={
        "user_id": "STRING",
        "item_id": "STRING", 
        "action_type": "STRING",
        "timestamp": "BIGINT",
        "amount": "DOUBLE"
    }
)

my_features = FeatureView(
    name="user_engagement",
    source=source,
    features=[
        Feature(
            name="click_count_5m",
            description="Number of clicks in last 5 minutes",
            aggregation=AggregationType.COUNT,
            source_field="*",
            filter_condition="action_type = 'click'"
        ),
        Feature(
            name="total_spend_5m",
            description="Total spending in last 5 minutes",
            aggregation=AggregationType.SUM,
            source_field="amount",
            filter_condition="action_type = 'purchase'"
        )
    ],
    window=Window(type=WindowType.TUMBLE, size_minutes=5),
    entity_key="user_id"
)
```

When the user describes features, generate valid Python code following this pattern.
Always include proper imports and complete, runnable code.
"""

FEATURE_ADVISOR_PROMPT = """You are a senior ML engineer specialized in feature engineering.
Analyze the user's data schema and use case, then recommend features that would be valuable.

Consider:
1. User engagement signals (recency, frequency, monetary value)
2. Temporal patterns (time-of-day, day-of-week effects)
3. Behavioral sequences (session patterns, conversion funnels)
4. Aggregate statistics (rolling averages, trends)
5. Cross-entity features (item popularity, user similarity)

For each recommendation, explain:
- What the feature captures
- Why it's valuable for the use case
- How to implement it with the SDK
"""

SDK_COPILOT_PROMPT = """You are the Feature Platform SDK Copilot.
Help users define, debug, and optimize their feature pipelines.

You can help with:
1. Writing feature definitions
2. Explaining how features are computed
3. Debugging pipeline issues
4. Optimizing feature performance
5. Best practices for feature engineering

The SDK uses:
- Apache Flink for stream processing
- Kafka for data ingestion
- Redis for feature storage
- Avro/Schema Registry for data contracts

Be concise and provide code examples when helpful.
"""


class LLMClient:
    """Unified LLM client supporting multiple providers."""
    
    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
        
        # Get API key from config or environment
        if self.config.api_key:
            api_key = self.config.api_key
        elif self.config.provider == LLMProvider.OPENAI:
            api_key = os.getenv("OPENAI_API_KEY")
        else:
            api_key = os.getenv("ANTHROPIC_API_KEY")
        
        if not api_key:
            raise ValueError(f"API key not found for {self.config.provider.value}")
        
        # Initialize client
        if self.config.provider == LLMProvider.OPENAI:
            if not OPENAI_AVAILABLE:
                raise ImportError("openai package not installed. Run: pip install openai")
            self.client = openai.OpenAI(api_key=api_key)
        else:
            if not ANTHROPIC_AVAILABLE:
                raise ImportError("anthropic package not installed. Run: pip install anthropic")
            self.client = anthropic.Anthropic(api_key=api_key)
    
    def chat(self, messages: List[Dict[str, str]], system_prompt: str = None) -> str:
        """Send chat messages and get response."""
        if self.config.provider == LLMProvider.OPENAI:
            return self._chat_openai(messages, system_prompt)
        else:
            return self._chat_anthropic(messages, system_prompt)
    
    def _chat_openai(self, messages: List[Dict[str, str]], system_prompt: str) -> str:
        all_messages = []
        if system_prompt:
            all_messages.append({"role": "system", "content": system_prompt})
        all_messages.extend(messages)
        
        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=all_messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens
        )
        return response.choices[0].message.content
    
    def _chat_anthropic(self, messages: List[Dict[str, str]], system_prompt: str) -> str:
        response = self.client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            system=system_prompt or "",
            messages=messages
        )
        return response.content[0].text


class FeatureGenerator:
    """Generate feature definitions from natural language."""
    
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
    
    def generate(self, description: str, source_schema: Optional[Dict] = None) -> str:
        """
        Generate feature definition code from natural language.
        
        Args:
            description: Natural language description of desired features
            source_schema: Optional dict of field_name -> type for the source
            
        Returns:
            Python code for the feature definition
        """
        user_message = f"Generate feature definitions for:\n{description}"
        
        if source_schema:
            schema_str = json.dumps(source_schema, indent=2)
            user_message += f"\n\nSource schema:\n{schema_str}"
        
        response = self.llm.chat(
            messages=[{"role": "user", "content": user_message}],
            system_prompt=FEATURE_DEFINITION_PROMPT
        )
        
        # Extract code block if present
        if "```python" in response:
            code = response.split("```python")[1].split("```")[0]
            return code.strip()
        elif "```" in response:
            code = response.split("```")[1].split("```")[0]
            return code.strip()
        
        return response


class FeatureAdvisor:
    """LLM-powered feature recommendations."""
    
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
    
    def recommend(
        self, 
        use_case: str, 
        source_schema: Dict[str, str],
        existing_features: Optional[List[str]] = None
    ) -> str:
        """
        Get feature recommendations for a use case.
        
        Args:
            use_case: Description of the ML use case (e.g., "click prediction", "fraud detection")
            source_schema: Dict of field_name -> type
            existing_features: List of already defined feature names
            
        Returns:
            Recommendations with explanations and code examples
        """
        message = f"""Use Case: {use_case}

Source Schema:
{json.dumps(source_schema, indent=2)}
"""
        
        if existing_features:
            message += f"\nExisting Features: {', '.join(existing_features)}"
        
        message += "\n\nPlease recommend 5 valuable features for this use case."
        
        return self.llm.chat(
            messages=[{"role": "user", "content": message}],
            system_prompt=FEATURE_ADVISOR_PROMPT
        )


class SDKCopilot:
    """Interactive assistant for feature engineering."""
    
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
        self.conversation_history: List[Dict[str, str]] = []
    
    def chat(self, message: str) -> str:
        """
        Send a message to the copilot and get a response.
        
        Args:
            message: User's question or request
            
        Returns:
            Copilot's response
        """
        self.conversation_history.append({"role": "user", "content": message})
        
        response = self.llm.chat(
            messages=self.conversation_history,
            system_prompt=SDK_COPILOT_PROMPT
        )
        
        self.conversation_history.append({"role": "assistant", "content": response})
        
        return response
    
    def reset(self):
        """Clear conversation history."""
        self.conversation_history = []


# Convenience functions for quick usage
def generate_features(description: str, api_key: str = None) -> str:
    """Quick function to generate features from description."""
    config = LLMConfig(api_key=api_key) if api_key else LLMConfig()
    client = LLMClient(config)
    generator = FeatureGenerator(client)
    return generator.generate(description)


def get_recommendations(use_case: str, schema: Dict[str, str], api_key: str = None) -> str:
    """Quick function to get feature recommendations."""
    config = LLMConfig(api_key=api_key) if api_key else LLMConfig()
    client = LLMClient(config)
    advisor = FeatureAdvisor(client)
    return advisor.recommend(use_case, schema)
