"""
Factory for an OpenAI-compatible client routed through the LiteLLM proxy.

All LLM calls in this project use make_llm_client() so that:
  - Every call routes through the LiteLLM proxy (localhost:4000)
  - The proxy's Langfuse callback captures token usage, cost, and latency
    automatically — no per-call instrumentation needed in application code
  - Model aliases (gpt-4o-mini, text-embedding-3-small) are resolved centrally
    in the proxy config, not scattered across the codebase

Grouping multiple LLM calls under a single Langfuse trace:
  Pass extra_body={"metadata": {"trace_id": trace_id, "generation_name": "..."}}
  to each completion call.  LiteLLM forwards this metadata to Langfuse so all
  generations in one user request appear under the same trace.

Environment variables (set in .env):
  LITELLM_BASE_URL  — proxy address, default http://localhost:4000
  LITELLM_API_KEY   — proxy API key, default sk-1234
"""

import os

from openai import OpenAI


def make_llm_client() -> OpenAI:
    """Return an OpenAI client pointed at the LiteLLM proxy."""
    return OpenAI(
        api_key=os.getenv("LITELLM_API_KEY", "sk-1234"),
        base_url=os.getenv("LITELLM_BASE_URL", "http://localhost:4000"),
    )


def litellm_metadata(trace_id: str, generation_name: str, session_id: str = None) -> dict:
    """
    Build the extra_body dict to pass trace context to the LiteLLM proxy.
    The proxy forwards this to Langfuse so all generations in one request
    appear under the same trace.

    Usage:
        client.chat.completions.create(
            model=..., messages=...,
            extra_body=litellm_metadata(trace_id, "classify"),
        )
    """
    metadata: dict = {"trace_id": trace_id, "generation_name": generation_name}
    if session_id:
        metadata["session_id"] = session_id
    return {"metadata": metadata}
