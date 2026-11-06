import re
from typing import Tuple, List


class IntentRouter:
    """
    Intelligent query classifier that routes natural language prompts to either
    live PostgreSQL database retrieval services or vector-store RAG documentation.
    Prevents hallucination of dynamic operational state.
    """

    LIVE_DB_KEYWORDS = [
        r"\bavailable\b",
        r"\bavailability\b",
        r"\bopen\s+bays?\b",
        r"\bdispensers?\b",
        r"\bmy\s+.*?(bookings?|reservations?|sessions?|charges?|history|spend)\b",
        r"\bhow much did i (spend|pay)\b",
        r"\bcurrent session\b",
        r"\bactive session\b",
        r"\bnearest station\b",
        r"\bclosest station\b",
        r"\bfind station\b",
        r"\bpredicted demand\b",
        r"\bforecast\b",
        r"\bhow busy\b",
        r"\bprice\b",
        r"\btariff\b",
        r"\brates?\b",
    ]

    POLICY_RAG_KEYWORDS = [
        r"\bpolicy\b",
        r"\bpolicies\b",
        r"\brules?\b",
        r"\bgrace period\b",
        r"\bcancel(lation)?\b",
        r"\bpenalt(y|ies)\b",
        r"\bidle fee\b",
        r"\bidling\b",
        r"\bconnector\b",
        r"\bccs2\b",
        r"\btype\s?2\b",
        r"\bchademo\b",
        r"\bsafety\b",
        r"\be-stop\b",
        r"\bemergency stop\b",
        r"\boverheating\b",
        r"\bcable stuck\b",
        r"\block(ed)?\b",
        r"\brefund\b",
        r"\bdispute\b",
        r"\brain\b",
        r"\bwet weather\b",
        r"\bcc-cv\b",
        r"\btaper(ing)?\b",
    ]

    @classmethod
    def classify_intent(cls, prompt: str) -> str:
        """
        Classifies prompt into 'LIVE_DATABASE', 'POLICY_RAG', 'HYBRID', or 'GENERAL'.
        """
        prompt_lower = prompt.lower()

        has_live_db = any(re.search(pat, prompt_lower) for pat in cls.LIVE_DB_KEYWORDS)
        has_policy_rag = any(re.search(pat, prompt_lower) for pat in cls.POLICY_RAG_KEYWORDS)

        if has_live_db and has_policy_rag:
            return "HYBRID"
        elif has_live_db:
            return "LIVE_DATABASE"
        elif has_policy_rag:
            return "POLICY_RAG"
        else:
            # Default to HYBRID so both knowledge sources can contribute
            return "HYBRID"
