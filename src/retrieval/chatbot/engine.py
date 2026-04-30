"""
Chatbot engine — orchestrates: classify → rewrite → retrieve → generate → format.

classify  →  IntentClassifier
rewrite   →  QueryRewriter
retrieve  →  DocRetriever | ArtifactRetriever | UserRetriever (or all for HYBRID)
generate  →  OpenAI chat completion with per-intent prompt template
format    →  formatter.format_response
"""

import logging
import os
from typing import Dict, List, Optional

from openai import OpenAI

from ..artifact_summary_store import ArtifactSummaryStore
from ..config import RetrievalConfig
from ..embeddings import EmbeddingService
from ..user_profile_store import UserProfileStore
from .classifier import IntentClassifier
from .doc_store import DocumentChunkStore
from .formatter import format_response
from .prompts import (
    build_artifact_search_messages,
    build_doc_qa_messages,
    build_hybrid_messages,
    build_user_search_messages,
)
from .query_rewriter import QueryRewriter
from .retrievers import ArtifactRetriever, DocRetriever, UserRetriever

logger = logging.getLogger(__name__)


class ChatEngine:
    """
    Single entry point for the enterprise chatbot.

    Usage:
        engine = ChatEngine(config, doc_store, artifact_store, user_store, embedding_service)
        result = engine.chat("How do I submit a Spark job?")
    """

    def __init__(
        self,
        config: RetrievalConfig,
        doc_store: DocumentChunkStore,
        artifact_store: ArtifactSummaryStore,
        user_store: UserProfileStore,
        embedding_service: EmbeddingService,
        llm_model: str = "gpt-4o-mini",
    ):
        self.config = config
        self.llm_model = llm_model

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set")
        self.client = OpenAI(api_key=api_key)

        self.classifier = IntentClassifier(model=llm_model)
        self.rewriter = QueryRewriter(model=llm_model)
        self.doc_retriever = DocRetriever(doc_store, embedding_service)
        self.artifact_retriever = ArtifactRetriever(artifact_store, embedding_service)
        self.user_retriever = UserRetriever(user_store, embedding_service)

    def chat(self, query: str, history: Optional[List[Dict]] = None) -> Dict:
        """
        Full pipeline: classify → rewrite → retrieve → generate → format.

        Returns the output schema dict.
        """
        history = history or []

        # 1. Classify
        classification = self.classifier.classify(query)
        intent = classification["intent"]
        confidence = classification["confidence"]
        logger.info(f"Intent: {intent} ({confidence:.2f}) — '{query}'")

        # 2. Rewrite query for better embedding recall
        search_query = self.rewriter.rewrite(query)

        # 3. Route & retrieve (deterministic, sources never mixed unless HYBRID)
        doc_hits: List[Dict] = []
        artifact_hits: List[Dict] = []
        user_hits: List[Dict] = []

        if intent == "DOC_QA":
            doc_hits = self.doc_retriever.retrieve(search_query, top_k=5)
        elif intent == "ARTIFACT_SEARCH":
            artifact_hits = self.artifact_retriever.retrieve(search_query, top_k=5)
        elif intent == "USER_SEARCH":
            user_hits = self.user_retriever.retrieve(search_query, top_k=5)
        elif intent == "HYBRID":
            doc_hits = self.doc_retriever.retrieve(search_query, top_k=3)
            artifact_hits = self.artifact_retriever.retrieve(search_query, top_k=3)
            user_hits = self.user_retriever.retrieve(search_query, top_k=3)

        # 4. Build prompt
        if intent == "DOC_QA":
            messages = build_doc_qa_messages(doc_hits, query)
        elif intent == "ARTIFACT_SEARCH":
            messages = build_artifact_search_messages(artifact_hits, query)
        elif intent == "USER_SEARCH":
            messages = build_user_search_messages(user_hits, query)
        else:  # HYBRID
            messages = build_hybrid_messages(doc_hits, artifact_hits, user_hits, query)

        # Inject conversation history between system and user turn
        if history:
            messages = [messages[0]] + history + [messages[-1]]

        # 5. Generate
        try:
            response = self.client.chat.completions.create(
                model=self.llm_model,
                messages=messages,
                temperature=0.2,
                max_tokens=800,
            )
            answer = response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            answer = "I encountered an error generating a response. Please try again."

        # 6. Format
        return format_response(
            answer=answer,
            intent=intent,
            confidence=confidence,
            raw_artifacts=artifact_hits,
            raw_users=user_hits,
            raw_docs=doc_hits,
        )
