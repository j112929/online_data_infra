"""
LLM-Powered Feature API

Provides REST endpoints for:
1. Natural Language Feature Generation
2. Feature Recommendations
3. SDK Copilot Chat
"""
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict
import os

app = FastAPI(
    title="Feature Platform LLM API",
    description="AI-powered feature engineering assistant",
    version="1.0.0"
)

# Import LLM components
from sdk.llm_integration import (
    LLMClient, LLMConfig, LLMProvider,
    FeatureGenerator, FeatureAdvisor, SDKCopilot
)

# Session storage for copilot conversations
copilot_sessions: Dict[str, SDKCopilot] = {}


def get_llm_client() -> LLMClient:
    """Dependency to get LLM client."""
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="No API key configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY"
        )
    
    # Detect provider from key format
    if api_key.startswith("sk-"):
        provider = LLMProvider.OPENAI
        model = "gpt-4o"
    else:
        provider = LLMProvider.ANTHROPIC
        model = "claude-3-sonnet-20240229"
    
    config = LLMConfig(provider=provider, api_key=api_key, model=model)
    return LLMClient(config)


# Request/Response Models
class GenerateRequest(BaseModel):
    description: str
    source_schema: Optional[Dict[str, str]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "description": "I want to track user clicks and views in the last 5 minutes, grouped by user_id",
                "source_schema": {
                    "user_id": "STRING",
                    "action_type": "STRING",
                    "item_id": "STRING",
                    "timestamp": "BIGINT"
                }
            }
        }


class GenerateResponse(BaseModel):
    code: str
    message: str


class RecommendRequest(BaseModel):
    use_case: str
    source_schema: Dict[str, str]
    existing_features: Optional[List[str]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "use_case": "Click-through rate prediction for a recommendation system",
                "source_schema": {
                    "user_id": "STRING",
                    "item_id": "STRING",
                    "action_type": "STRING",
                    "timestamp": "BIGINT",
                    "price": "DOUBLE"
                },
                "existing_features": ["click_count_1m"]
            }
        }


class RecommendResponse(BaseModel):
    recommendations: str


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "How do I create a feature that counts purchases in the last hour?",
                "session_id": "user-123"
            }
        }


class ChatResponse(BaseModel):
    response: str
    session_id: str


# Endpoints
@app.post("/llm/generate", response_model=GenerateResponse, tags=["LLM"])
async def generate_features(request: GenerateRequest):
    """
    Generate feature definition code from natural language.
    
    Describe what features you want in plain English, and the LLM will
    generate the corresponding SDK code.
    """
    try:
        client = get_llm_client()
        generator = FeatureGenerator(client)
        code = generator.generate(request.description, request.source_schema)
        
        return GenerateResponse(
            code=code,
            message="Feature definition generated successfully. Copy to sdk/feature_definition.py"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/llm/recommend", response_model=RecommendResponse, tags=["LLM"])
async def recommend_features(request: RecommendRequest):
    """
    Get AI-powered feature recommendations for your use case.
    
    Describe your ML use case and provide your data schema to get
    personalized feature engineering recommendations.
    """
    try:
        client = get_llm_client()
        advisor = FeatureAdvisor(client)
        recommendations = advisor.recommend(
            request.use_case,
            request.source_schema,
            request.existing_features
        )
        
        return RecommendResponse(recommendations=recommendations)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/llm/chat", response_model=ChatResponse, tags=["LLM"])
async def chat_with_copilot(request: ChatRequest):
    """
    Chat with the SDK Copilot.
    
    Ask questions about feature engineering, get help with SDK usage,
    debug issues, and learn best practices.
    
    Use session_id to maintain conversation context across requests.
    """
    try:
        session_id = request.session_id
        
        # Get or create copilot session
        if session_id not in copilot_sessions:
            client = get_llm_client()
            copilot_sessions[session_id] = SDKCopilot(client)
        
        copilot = copilot_sessions[session_id]
        response = copilot.chat(request.message)
        
        return ChatResponse(response=response, session_id=session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/llm/chat/{session_id}", tags=["LLM"])
async def clear_chat_session(session_id: str):
    """Clear a copilot chat session."""
    if session_id in copilot_sessions:
        del copilot_sessions[session_id]
        return {"message": f"Session {session_id} cleared"}
    return {"message": f"Session {session_id} not found"}


@app.get("/llm/health", tags=["LLM"])
async def llm_health():
    """Check LLM API availability."""
    openai_key = bool(os.getenv("OPENAI_API_KEY"))
    anthropic_key = bool(os.getenv("ANTHROPIC_API_KEY"))
    
    return {
        "status": "ok" if (openai_key or anthropic_key) else "no_api_key",
        "openai_configured": openai_key,
        "anthropic_configured": anthropic_key,
        "active_sessions": len(copilot_sessions)
    }
