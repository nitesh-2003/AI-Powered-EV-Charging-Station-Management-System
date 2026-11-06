import os
import json
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.assistant import ChatRequest, ChatResponse, ChatSource, ChatMessage
from app.ai.assistant.router import IntentRouter
from app.ai.assistant.indexer import knowledge_indexer
from app.ai.assistant.live_retriever import LiveDataRetriever


SYSTEM_INSTRUCTION = """You are VoltFlow AI Mobility Assistant, an enterprise-grade artificial intelligence supporting EV drivers and network operators.
Your responsibilities:
1. Provide accurate, verified answers about EV charging station availability, connector standards, pricing, reservations, and operating policies.
2. Ground all factual statements strictly in the provided Context and Live Database records.
3. NEVER hallucinate or assume station availability, pricing rates, or user booking records not explicitly stated in the context.
4. If asked about policies (e.g. cancellations, idling fees, cable release), cite the relevant policy rule accurately.
5. Format your output with clear, concise bullet points and bold highlights for readability.
"""


class RAGEngine:
    """
    Hybrid Retrieval-Augmented Generation Engine.
    Coordinates query routing, ChromaDB semantic vector search,
    real-time database state retrieval, and grounded response synthesis.
    """

    def __init__(self):
        self.indexer = knowledge_indexer
        self.router = IntentRouter()

    def process_chat(
        self,
        db: Session,
        user: User,
        request: ChatRequest,
    ) -> ChatResponse:
        """
        Executes the full RAG pipeline:
        1. Classifies intent (LIVE_DATABASE vs POLICY_RAG vs HYBRID).
        2. Retrieves live operational state from PostgreSQL if applicable.
        3. Retrieves relevant policy chunks from ChromaDB vector store if applicable.
        4. Synthesizes a grounded, accurate response with transparent source citations.
        """
        user_prompt = request.message.strip()
        intent = self.router.classify_intent(user_prompt)

        sources: List[ChatSource] = []
        live_facts: Dict[str, Any] = {}
        retrieved_docs: List[Dict[str, Any]] = []

        # 1. LIVE DATABASE RETRIEVAL
        if intent in ["LIVE_DATABASE", "HYBRID"]:
            # Station availability
            st_summary = LiveDataRetriever.get_live_stations_summary(db=db)
            live_facts["network_stations"] = st_summary

            if any(w in user_prompt.lower() for w in ["station", "open", "available", "where", "nearest", "cost", "price"]):
                station_snippets = []
                for st in st_summary["stations"][:4]:
                    station_snippets.append(
                        f"• {st['station_name']} ({st['address']}): {st['available_bays']}/{st['total_bays']} bays available. "
                        f"Power: {st['max_power_kw']}, Tariff: {st['starting_price_per_kwh']}/kWh, Connectors: {', '.join(st['connectors'])}."
                    )
                sources.append(
                    ChatSource(
                        title="Live Station Network Database",
                        source_type="LIVE_DATABASE",
                        snippet="\n".join(station_snippets),
                    )
                )

            # User personal history
            if any(w in user_prompt.lower() for w in ["my", "booking", "reservation", "session", "charge", "spent", "history"]):
                user_act = LiveDataRetriever.get_user_activity(db=db, user=user)
                live_facts["user_activity"] = user_act

                user_snippets = []
                if user_act["recent_bookings"]:
                    b_strs = [f"Booking {b['booking_id']} at {b['station']} ({b['status']}) on {b['start_time']}" for b in user_act['recent_bookings'][:2]]
                    user_snippets.append("Active/Recent Bookings: " + "; ".join(b_strs))
                if user_act["recent_sessions"]:
                    s_strs = [f"Session {s['session_id']} ({s['energy_kwh']}, {s['total_cost']})" for s in user_act['recent_sessions'][:2]]
                    user_snippets.append("Recent Sessions: " + "; ".join(s_strs))
                user_snippets.append(f"Total Billed: {user_act['total_amount_billed']} for {user_act['total_kwh_delivered']} kWh")

                sources.append(
                    ChatSource(
                        title=f"User Account Activity ({user.full_name})",
                        source_type="LIVE_DATABASE",
                        snippet=" | ".join(user_snippets),
                    )
                )

        # 2. VECTOR SEARCH (CHROMADB POLICY RETRIEVAL)
        if intent in ["POLICY_RAG", "HYBRID"]:
            search_results = self.indexer.search(query_text=user_prompt, n_results=3)
            retrieved_docs = search_results

            for res in search_results:
                sources.append(
                    ChatSource(
                        title=f"{res['metadata'].get('doc_title', 'Network Guide')} > {res['section_header']}",
                        source_type="POLICY_RAG",
                        snippet=res["text"][:280] + ("..." if len(res["text"]) > 280 else ""),
                    )
                )

        # 3. RESPONSE SYNTHESIS (Grounded Generation)
        answer = self._synthesize_grounded_response(
            prompt=user_prompt,
            intent=intent,
            live_facts=live_facts,
            retrieved_docs=retrieved_docs,
            user=user,
        )

        return ChatResponse(
            answer=answer,
            intent=intent,
            sources=sources,
        )

    def _synthesize_grounded_response(
        self,
        prompt: str,
        intent: str,
        live_facts: Dict[str, Any],
        retrieved_docs: List[Dict[str, Any]],
        user: User,
    ) -> str:
        """
        Synthesizes response with strict grounding.
        If external LLM API key is present, passes context to model;
        otherwise executes deterministic grounded synthesis.
        """
        prompt_lower = prompt.lower()
        response_parts = []

        # Check if external LLM API is available (e.g. Gemini / OpenAI)
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                return self._call_external_llm(prompt, live_facts, retrieved_docs, user)
            except Exception as e:
                print(f"Warning: External LLM call failed ({e}); falling back to local grounded synthesis.")

        # LOCAL DETERMINISTIC GROUNDED SYNTHESIS ENGINE
        is_policy_query = any(w in prompt_lower for w in ["grace period", "policy", "policies", "cancel", "fee", "penalty", "idle", "safety", "rain", "connector", "ccs2", "type 2", "rules"])
        is_personal_lookup = "my" in prompt_lower and any(w in prompt_lower for w in ["history", "session", "charge", "booking", "spend", "reservation", "account"])

        # Handle user personal booking / charging history
        if is_personal_lookup and not is_policy_query:
            act = live_facts.get("user_activity", {})
            bookings = act.get("recent_bookings", [])
            sessions = act.get("recent_sessions", [])

            response_parts.append(f"Hello **{user.full_name}**, here is your verified account summary:")
            if bookings:
                response_parts.append("\n**Your Active & Recent Reservations:**")
                for b in bookings:
                    response_parts.append(f"- **{b['station']}** ({b['dispenser']}): `{b['status']}` from {b['start_time']} to {b['end_time']}.")
            else:
                response_parts.append("\n- You currently have no active slot reservations.")

            if sessions:
                response_parts.append(f"\n**Your Charging History & Spend:**")
                for s in sessions:
                    response_parts.append(f"- Session `{s['session_id']}`: Delivered **{s['energy_kwh']}** for **{s['total_cost']}** (Status: `{s['status']}`).")
                response_parts.append(f"\n*Cumulative energy billed:* **{act.get('total_kwh_delivered')} kWh** (**{act.get('total_amount_billed')}**).")
            return "\n".join(response_parts)

        # Handle policy questions (cancellation, grace period, idle fee, safety, connector standards)
        if retrieved_docs:
            response_parts.append("**Network Operating Policies & Guidelines:**")
            for doc in retrieved_docs[:2]:
                text = doc["text"]
                # Clean header formatting for chat output
                lines = [l for l in text.split("\n") if l.strip()]
                response_parts.append("\n" + "\n".join(lines[:6]))

        # Handle station availability & live pricing
        if any(w in prompt_lower for w in ["available", "station", "open", "nearest", "cost", "price", "tariff"]):
            st_data = live_facts.get("network_stations", {}).get("stations", [])
            if st_data:
                if response_parts:
                    response_parts.append("\n---")
                response_parts.append("Here is the current live availability across our charging network:")
                for st in st_data:
                    status_badge = "✅ Open Bays" if st["available_bays"] > 0 else "🔴 Fully Occupied"
                    response_parts.append(
                        f"\n• **{st['station_name']}** ({status_badge})\n"
                        f"  - **Address:** {st['address']}\n"
                        f"  - **Availability:** {st['available_bays']} of {st['total_bays']} bays free\n"
                        f"  - **Max Power:** {st['max_power_kw']} | **Tariff:** from {st['starting_price_per_kwh']}/kWh\n"
                        f"  - **Connectors:** {', '.join(st['connectors'])}"
                    )

        if not response_parts:
            response_parts.append(
                "I am your **VoltFlow EV Assistant**. I can help you with:\n"
                "• **Live Station Availability:** Check which charging bays are currently open.\n"
                "• **Your Personal Account:** Review your active bookings, past charging sessions, and invoices.\n"
                "• **Operating Policies:** Learn about our 15-minute grace period, cancellation rules, and anti-idling fees.\n"
                "• **Technical Guidance:** Assistance with CCS2/Type 2 connectors, cable lock issues, and rainy weather safety."
            )

        return "\n".join(response_parts)

    def _call_external_llm(
        self,
        prompt: str,
        live_facts: Dict[str, Any],
        retrieved_docs: List[Dict[str, Any]],
        user: User,
    ) -> str:
        """Invokes external LLM API if key is supplied in .env."""
        import urllib.request
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("No GEMINI_API_KEY")

        context_str = f"User Name: {user.full_name} (Role: {user.role})\n\n"
        if live_facts:
            context_str += f"LIVE DATABASE GROUND TRUTH:\n{json.dumps(live_facts, indent=2)}\n\n"
        if retrieved_docs:
            context_str += "RETRIEVED KNOWLEDGE BASE POLICY CHUNKS:\n"
            for d in retrieved_docs:
                context_str += f"---\n{d['text']}\n"

        full_prompt = f"{SYSTEM_INSTRUCTION}\n\nCONTEXT:\n{context_str}\n\nUSER QUESTION: {prompt}\n\nANSWER:"
        # Call Gemini REST endpoint
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        payload = json.dumps({"contents": [{"parts": [{"text": full_prompt}]}]}).encode("utf-8")

        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=12) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result["candidates"][0]["content"]["parts"][0]["text"].strip()


# Global singleton instance
rag_assistant = RAGEngine()
