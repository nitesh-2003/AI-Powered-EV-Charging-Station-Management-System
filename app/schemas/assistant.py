from datetime import datetime, timezone
from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class ChatSource(BaseModel):
    """Source attribution for grounding and auditability."""
    title: str
    source_type: str = Field(..., description="'LIVE_DATABASE', 'POLICY_RAG', 'TECHNICAL_GUIDE'")
    snippet: str


class ChatMessage(BaseModel):
    """Single message in conversational turn."""
    role: str = Field(..., description="'user' or 'assistant' or 'system'")
    content: str


class ChatRequest(BaseModel):
    """Driver or Administrator natural language prompt payload."""
    message: str = Field(..., min_length=1, max_length=1000, description="Natural language question")
    history: Optional[List[ChatMessage]] = Field(default=[], description="Prior conversational context")
    user_latitude: Optional[float] = Field(None, description="Optional user GPS latitude for location-aware queries")
    user_longitude: Optional[float] = Field(None, description="Optional user GPS longitude for location-aware queries")


class ChatResponse(BaseModel):
    """Grounded AI Assistant reply with transparent sources."""
    answer: str
    intent: str = Field(..., description="'LIVE_DATABASE', 'POLICY_RAG', 'HYBRID', 'GENERAL'")
    sources: List[ChatSource]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

