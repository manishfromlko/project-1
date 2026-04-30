"""Intent classifier: maps user query → DOC_QA | ARTIFACT_SEARCH | USER_SEARCH | HYBRID."""

import json
import logging
import os
from typing import Dict

from openai import OpenAI

logger = logging.getLogger(__name__)

INTENTS = {"DOC_QA", "ARTIFACT_SEARCH", "USER_SEARCH", "HYBRID"}

_SYSTEM_PROMPT = """\
You are an intent classifier for an enterprise knowledge assistant.

Classify the user query into exactly one of the following intents:

1. DOC_QA → questions about platform usage, how-to guides, concepts, onboarding steps
2. ARTIFACT_SEARCH → requests to find code examples, notebooks, scripts, implementations, datasets
3. USER_SEARCH → requests to find people, owners, experts, who-works-on-what
4. HYBRID → the query combines two or more of the above intents

Return ONLY a JSON object with this exact structure:
{
  "intent": "<DOC_QA|ARTIFACT_SEARCH|USER_SEARCH|HYBRID>",
  "confidence": <float 0-1>,
  "reasoning": "<one short sentence>"
}

Do not include any other text."""


class IntentClassifier:
    """Uses an LLM to classify query intent."""

    def __init__(self, model: str = "gpt-4o-mini"):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set")
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def classify(self, query: str) -> Dict:
        """
        Returns dict: {intent, confidence, reasoning}
        Falls back to DOC_QA with low confidence on failure.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": f"Query: {query}"},
                ],
                temperature=0.0,
                max_tokens=150,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content
            result = json.loads(raw)

            intent = result.get("intent", "DOC_QA").upper()
            if intent not in INTENTS:
                intent = "DOC_QA"

            return {
                "intent": intent,
                "confidence": float(result.get("confidence", 0.5)),
                "reasoning": result.get("reasoning", ""),
            }
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            return {"intent": "DOC_QA", "confidence": 0.3, "reasoning": f"Classification error: {e}"}
