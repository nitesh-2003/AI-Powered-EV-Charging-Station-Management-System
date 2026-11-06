from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.schemas.assistant import ChatRequest, ChatResponse
from app.ai.assistant.rag_engine import rag_assistant
from app.ai.assistant.indexer import knowledge_indexer

router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Natural Language AI Assistant (Hybrid RAG + Live DB)",
)
def chat_with_assistant(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Enterprise RAG Assistant combining semantic vector retrieval (ChromaDB)
    for operating policies, connector guides, and troubleshooting with
    real-time PostgreSQL queries for verified live bay availability and driver history.
    """
    return rag_assistant.process_chat(db=db, user=current_user, request=request)


@router.get(
    "/knowledge-base-stats",
    summary="Returns stats on indexed vector chunks in ChromaDB",
)
def get_knowledge_base_stats(
    current_user: User = Depends(get_current_active_user),
):
    """Returns vector store collection stats."""
    return {
        "collection_name": knowledge_indexer.collection.name,
        "total_indexed_chunks": knowledge_indexer.collection.count(),
        "vector_dimensions": 384,
        "distance_metric": "cosine",
    }

