"""Structured response formatter — enforces the output schema."""

import re
from typing import Dict, List


def _extract_artifacts_from_text(text: str, raw_artifacts: List[Dict]) -> List[Dict]:
    """Build artifact list from retrieval hits that the LLM referenced."""
    result = []
    for a in raw_artifacts:
        artifact_id = a.get("artifact_id", "")
        summary = a.get("artifact_summary", "")
        if artifact_id and (artifact_id in text or summary[:40] in text):
            result.append({
                "title": artifact_id,
                "reason": "Referenced in response",
                "owner": a.get("user_id", "unknown"),
            })
    return result


def _extract_users_from_text(text: str, raw_users: List[Dict]) -> List[Dict]:
    """Build user list from retrieval hits that the LLM referenced."""
    result = []
    for u in raw_users:
        user_id = u.get("user_id", "")
        if user_id and user_id in text:
            tags = [t.strip() for t in u.get("tags", "").split(",") if t.strip()]
            result.append({
                "name": user_id,
                "reason": "Referenced in response",
                "skills": tags,
            })
    return result


def format_response(
    answer: str,
    intent: str,
    confidence: float,
    raw_artifacts: List[Dict] = None,
    raw_users: List[Dict] = None,
    raw_docs: List[Dict] = None,
) -> Dict:
    """
    Build the canonical output schema:
    {answer, intent, confidence, artifacts, users, sources}
    """
    raw_artifacts = raw_artifacts or []
    raw_users = raw_users or []
    raw_docs = raw_docs or []

    artifacts = []
    users = []

    if intent in ("ARTIFACT_SEARCH", "HYBRID"):
        # Include all retrieved artifacts as the LLM was instructed to use them
        for a in raw_artifacts:
            artifacts.append({
                "title": a.get("artifact_id", "unknown"),
                "reason": "Retrieved as relevant artifact",
                "owner": a.get("user_id", "unknown"),
            })

    if intent in ("USER_SEARCH", "HYBRID"):
        for u in raw_users:
            tags = [t.strip() for t in u.get("tags", "").split(",") if t.strip()]
            users.append({
                "name": u.get("user_id", "unknown"),
                "reason": "Retrieved as relevant user",
                "skills": tags,
            })

    sources = []
    if intent in ("DOC_QA", "HYBRID"):
        seen = set()
        for d in raw_docs:
            sf = d.get("source_file", "")
            if sf and sf not in seen:
                seen.add(sf)
                sources.append({"file": sf, "doc_id": d.get("doc_id", "")})

    return {
        "answer": answer.strip(),
        "intent": intent,
        "confidence": round(confidence, 3),
        "artifacts": artifacts,
        "users": users,
        "sources": sources,
    }
