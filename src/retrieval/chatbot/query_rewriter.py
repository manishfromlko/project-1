"""Query rewriting layer — optimise user query for semantic search."""

import logging
import os

from openai import OpenAI

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
Rewrite the user's question into a concise, keyword-rich search query optimised for semantic vector search.

Rules:
- Remove filler words ("can you", "please", "I want to")
- Expand abbreviations if obvious
- Add synonyms in parentheses if helpful
- Keep under 30 words
- Return ONLY the rewritten query, no explanation"""


class QueryRewriter:
    def __init__(self, model: str = "gpt-4o-mini"):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set")
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def rewrite(self, query: str) -> str:
        """Return a semantically enriched query string."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": query},
                ],
                temperature=0.0,
                max_tokens=80,
            )
            rewritten = response.choices[0].message.content.strip()
            logger.debug(f"Query rewritten: '{query}' → '{rewritten}'")
            return rewritten or query
        except Exception as e:
            logger.warning(f"Query rewriting failed, using original: {e}")
            return query
