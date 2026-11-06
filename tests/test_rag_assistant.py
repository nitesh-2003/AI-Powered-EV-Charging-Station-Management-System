import uuid
import pytest

from app.schemas.assistant import ChatRequest
from app.ai.assistant.indexer import knowledge_indexer
from app.ai.assistant.router import IntentRouter
from app.ai.assistant.rag_engine import rag_assistant
from app.models.user import User


def test_knowledge_base_indexing_and_count():
    """Verify that all markdown policy files were parsed and stored in ChromaDB."""
    count = knowledge_indexer.collection.count()
    assert count > 0, "ChromaDB knowledge base collection should not be empty."


def test_vector_similarity_search_retrieval():
    """Verify that semantic search retrieves relevant chunks with high cosine similarity."""
    # 1. Search for cancellation policy
    results = knowledge_indexer.search("cancellation penalty window", n_results=2)
    assert len(results) > 0
    top_result = results[0]
    assert "cancellation" in top_result["text"].lower() or "penalty" in top_result["text"].lower()
    assert top_result["similarity"] > 0.0

    # 2. Search for rainy weather safety
    weather_results = knowledge_indexer.search("charging electric vehicle in rain wet weather", n_results=1)
    assert len(weather_results) > 0
    assert "rain" in weather_results[0]["text"].lower() or "wet" in weather_results[0]["text"].lower()


def test_intent_router_classification():
    """Verify that the router separates live database intents from static policy queries."""
    # Live database queries
    assert IntentRouter.classify_intent("How many charging bays are available right now?") == "LIVE_DATABASE"
    assert IntentRouter.classify_intent("Show me my recent charging sessions and history") == "LIVE_DATABASE"

    # Policy RAG queries
    assert IntentRouter.classify_intent("What is the penalty fee if I cancel my slot late?") == "POLICY_RAG"
    assert IntentRouter.classify_intent("What is an idle fee and when does it apply?") == "POLICY_RAG"
    assert IntentRouter.classify_intent("Is it safe to charge during rain and snow?") == "POLICY_RAG"

    # Hybrid queries
    assert IntentRouter.classify_intent("What is the price per kWh at Downtown station and what is your cancellation policy?") == "HYBRID"


def test_rag_engine_grounded_response_generation():
    """Verify that the assistant synthesizes grounded responses with sources."""
    mock_user = User(
        id=uuid.uuid4(),
        email="driver.tester@example.com",
        full_name="Alice EV Driver",
        role="CUSTOMER",
        is_active=True,
    )

    class MockDB:
        def query(self, model):
            class Q:
                def filter(self, *a):
                    return self
                def order_by(self, *a):
                    return self
                def limit(self, *a):
                    return self
                def all(self):
                    return []
                def count(self):
                    return 0
            return Q()

    db = MockDB()

    # Query 1: Policy question
    req_policy = ChatRequest(message="What is the grace period before my booking is cancelled?")
    res_policy = rag_assistant.process_chat(db=db, user=mock_user, request=req_policy)
    assert len(res_policy.sources) > 0
    assert "15-minute" in res_policy.answer or "grace period" in res_policy.answer.lower()
    assert any(s.source_type == "POLICY_RAG" for s in res_policy.sources)

    # Query 2: Personal account inquiry
    req_account = ChatRequest(message="Show me my recent charging history and spend")
    res_account = rag_assistant.process_chat(db=db, user=mock_user, request=req_account)
    assert "Alice EV Driver" in res_account.answer
    assert any(s.source_type == "LIVE_DATABASE" for s in res_account.sources)

