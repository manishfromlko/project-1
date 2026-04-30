"""Modular prompt templates — one per intent."""

from typing import Dict, List

DOC_QA_SYSTEM = """\
You are a platform expert assistant. Answer ONLY using the provided documentation context.

Rules:
- If the answer is not present in the context, say exactly: "I don't see this information in the platform knowledge base."
- Be concise. Use numbered steps for procedural answers.
- Never fabricate information beyond what is in the context.
- Cite the source document name when relevant."""

DOC_QA_USER = """\
Documentation context:
{retrieved_chunks}

Question: {user_query}

Answer:"""


ARTIFACT_SEARCH_SYSTEM = """\
You are a code artifact discovery assistant. Help users find relevant notebooks, scripts, and implementations.

Rules:
- ONLY reference artifacts provided in the context below.
- Do NOT invent artifact names or details.
- Be concise and structured.
- If no relevant artifacts are found, say: "I couldn't find any matching artifacts in the workspace." """

ARTIFACT_SEARCH_USER = """\
Artifact summaries:
{artifact_results}

User query: {user_query}

Return a structured list of relevant artifacts, why each is relevant, and what problem it solves."""


USER_SEARCH_SYSTEM = """\
You are a people-finder assistant for a data science platform. Help users identify relevant colleagues.

Rules:
- ONLY reference users provided in the context below.
- Do not make assumptions beyond the provided profiles.
- Keep output structured.
- If no relevant users are found, say: "I couldn't find matching users for this query." """

USER_SEARCH_USER = """\
User profiles:
{user_results}

Query: {user_query}

Return a structured list of relevant users, their expertise, and why they match."""


HYBRID_SYSTEM = """\
You are a comprehensive enterprise knowledge assistant. Combine multiple sources to answer the query.

Rules:
- Only reference sources explicitly provided below.
- Clearly separate: direct answer, supporting artifacts, relevant people.
- Never hallucinate. If a source has no relevant data, omit that section.
- If no relevant data exists at all, say so explicitly."""

HYBRID_USER = """\
Documentation chunks:
{doc_chunks}

Artifact summaries:
{artifact_results}

User profiles:
{user_results}

Query: {user_query}

Provide a comprehensive response with direct answer, supporting artifacts, and relevant users."""


def build_doc_qa_messages(retrieved_chunks: List[Dict], user_query: str) -> List[Dict]:
    chunk_text = "\n\n---\n\n".join(
        f"[{c.get('source_file', 'unknown')}]\n{c.get('chunk_text', '')}"
        for c in retrieved_chunks
    )
    return [
        {"role": "system", "content": DOC_QA_SYSTEM},
        {"role": "user", "content": DOC_QA_USER.format(
            retrieved_chunks=chunk_text or "No documentation found.",
            user_query=user_query,
        )},
    ]


def build_artifact_search_messages(artifact_results: List[Dict], user_query: str) -> List[Dict]:
    artifact_text = "\n\n---\n\n".join(
        f"Artifact: {a.get('artifact_id', 'unknown')}\nOwner: {a.get('user_id', 'unknown')}\n"
        f"Tags: {a.get('tags', '')}\nSummary: {a.get('artifact_summary', '')}"
        for a in artifact_results
    )
    return [
        {"role": "system", "content": ARTIFACT_SEARCH_SYSTEM},
        {"role": "user", "content": ARTIFACT_SEARCH_USER.format(
            artifact_results=artifact_text or "No artifacts found.",
            user_query=user_query,
        )},
    ]


def build_user_search_messages(user_results: List[Dict], user_query: str) -> List[Dict]:
    user_text = "\n\n---\n\n".join(
        f"User: {u.get('user_id', 'unknown')}\nTags: {u.get('tags', '')}\nProfile: {u.get('user_profile', '')}"
        for u in user_results
    )
    return [
        {"role": "system", "content": USER_SEARCH_SYSTEM},
        {"role": "user", "content": USER_SEARCH_USER.format(
            user_results=user_text or "No user profiles found.",
            user_query=user_query,
        )},
    ]


def build_hybrid_messages(
    doc_chunks: List[Dict],
    artifact_results: List[Dict],
    user_results: List[Dict],
    user_query: str,
) -> List[Dict]:
    doc_text = "\n\n---\n\n".join(
        f"[{c.get('source_file', 'unknown')}]\n{c.get('chunk_text', '')}" for c in doc_chunks
    )
    artifact_text = "\n\n---\n\n".join(
        f"Artifact: {a.get('artifact_id', 'unknown')}\nOwner: {a.get('user_id', 'unknown')}\n"
        f"Summary: {a.get('artifact_summary', '')}"
        for a in artifact_results
    )
    user_text = "\n\n---\n\n".join(
        f"User: {u.get('user_id', 'unknown')}\nProfile: {u.get('user_profile', '')}"
        for u in user_results
    )
    return [
        {"role": "system", "content": HYBRID_SYSTEM},
        {"role": "user", "content": HYBRID_USER.format(
            doc_chunks=doc_text or "No documentation found.",
            artifact_results=artifact_text or "No artifacts found.",
            user_results=user_text or "No user profiles found.",
            user_query=user_query,
        )},
    ]
