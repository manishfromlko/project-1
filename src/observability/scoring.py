"""
Trace scoring utilities for the RAG pipeline.

The LiteLLM proxy automatically logs all LLM API calls to Langfuse (tokens,
cost, latency, prompt/response).  This module's sole job is posting *scores*
onto those traces — something the proxy doesn't do on its own.

Two scoring modes:
  1. User feedback   — thumbs up / down from the chat UI (via /observability/feedback)
  2. Auto heuristic  — lightweight quality signals computed from the response,
                       posted immediately after generation (no extra LLM call)

RAGAS-based scoring (faithfulness, context relevance, answer relevance) is
Layer 2 and is not included here.

All functions are no-ops when LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY are unset.

Environment variables:
  LANGFUSE_PUBLIC_KEY  — Langfuse project public key
  LANGFUSE_SECRET_KEY  — Langfuse project secret key
  LANGFUSE_HOST        — Langfuse server URL (default http://localhost:3000)
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Heuristic thresholds
_MIN_ANSWER_CHARS = 50
_MAX_ANSWER_CHARS = 2000

try:
    from langfuse import Langfuse
    _LANGFUSE_AVAILABLE = True
except ImportError:
    _LANGFUSE_AVAILABLE = False

_langfuse_instance = None


def _get_langfuse():
    global _langfuse_instance
    if _langfuse_instance is not None:
        return _langfuse_instance
    if not _LANGFUSE_AVAILABLE:
        return None
    pk = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    sk = os.getenv("LANGFUSE_SECRET_KEY", "")
    if not pk or pk.startswith("your-"):
        return None
    _langfuse_instance = Langfuse(
        public_key=pk,
        secret_key=sk,
        host=os.getenv("LANGFUSE_HOST", "http://localhost:3000"),
    )
    return _langfuse_instance


def score_trace(
    trace_id: str,
    name: str,
    value: float,
    comment: Optional[str] = None,
) -> None:
    """Post a named score to a Langfuse trace. value must be in [0, 1]."""
    lf = _get_langfuse()
    if not lf or not trace_id:
        return
    try:
        lf.score(
            trace_id=trace_id,
            name=name,
            value=round(float(value), 4),
            comment=comment,
        )
    except Exception as e:
        logger.warning(f"Failed to post score '{name}' to trace {trace_id}: {e}")


def score_user_feedback(trace_id: str, thumbs_up: bool) -> None:
    """
    Record binary user feedback (thumbs up = 1.0, thumbs down = 0.0).
    Appears in Langfuse as score name 'user_feedback'.
    """
    score_trace(
        trace_id=trace_id,
        name="user_feedback",
        value=1.0 if thumbs_up else 0.0,
        comment="thumbs_up" if thumbs_up else "thumbs_down",
    )


def score_response_quality(trace_id: str, answer: str, intent: str) -> None:
    """
    Lightweight heuristic quality scoring — no LLM call, runs inline.

    Scores posted:
      response_length   — normalised answer length (penalises very short/long)
      has_content       — 1.0 if answer looks substantive, 0.0 if it's a fallback
    """
    if not trace_id or not answer:
        return

    # response_length: peak at ~300 chars, taper on either end
    n = len(answer.strip())
    if n < _MIN_ANSWER_CHARS:
        length_score = n / _MIN_ANSWER_CHARS * 0.5
    elif n <= 300:
        length_score = 0.5 + (n - _MIN_ANSWER_CHARS) / (300 - _MIN_ANSWER_CHARS) * 0.5
    elif n <= _MAX_ANSWER_CHARS:
        length_score = 1.0
    else:
        length_score = max(0.5, 1.0 - (n - _MAX_ANSWER_CHARS) / _MAX_ANSWER_CHARS * 0.3)

    fallback_phrases = [
        "i couldn't find",
        "i don't have access",
        "i encountered an error",
        "please try again",
        "outside what i can help",
    ]
    has_content = 0.0 if any(p in answer.lower() for p in fallback_phrases) else 1.0

    score_trace(trace_id, "response_length", length_score, f"answer_chars={n}")
    score_trace(trace_id, "has_content", has_content, f"intent={intent}")
