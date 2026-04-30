# Kubeflow Workspace Profiling Webapp

A generative AI-powered web application for profiling and analyzing Kubeflow workspaces. Provides intelligent insights into data science workflows, ML pipelines, and collaboration patterns through automated data ingestion, vector search, and LLM-powered analysis — plus an enterprise chatbot for docs QA, artifact discovery, and people search.

## Architecture Overview

```
Phase 1: Data Ingestion       →  dataset/.ingestion/ingestion_catalog.json
Phase 2: Vector Retrieval     →  Milvus (port 19530) + FastAPI (port 8000)
Phase 3: Webapp Frontend      →  Next.js (port 3000) — proxies /api/* to FastAPI
Phase 4: LLM Generation       →  User profiles, artifact summaries, AI chatbot
```

**How the webapp talks to the backend:**
The Next.js webapp does NOT call the Python backend directly from the browser.
It has server-side API route handlers at `/api/*` (in `webapp/app/api/`) that proxy and
transform requests to the Python FastAPI backend. The Python backend URL is configured
via `PYTHON_API_URL` (default: `http://localhost:8000`).

## Prerequisites

- Python 3.11+
- Docker (for Milvus vector database)
- Node.js 18+
- OpenAI API key (embeddings + LLM generation)

---

## Step-by-Step: Running the Full Stack

### Step 1 — Install Python dependencies

This project uses `uv` for dependency management. If you don't have it:

```bash
pip install uv
```

Install all dependencies into a managed virtual environment:

```bash
uv sync
```

Or with a traditional venv:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 2 — Create the `.env` file

Create a `.env` file at the project root (already gitignored):

```bash
cat > .env <<'EOF'
OPENAI_API_KEY=<your-openai-api-key>
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536
INGESTION_CATALOG_PATH=dataset/.ingestion/ingestion_catalog.json
PROFILE_LLM_MODEL=gpt-4o-mini
EOF
```

The Python backend loads `.env` automatically at startup.

> **Note:** A valid `OPENAI_API_KEY` is required for embeddings and all LLM features. The server refuses to start without it.

### Step 3 — Run the data ingestion pipeline

Catalogues Jupyter notebooks (`.ipynb`), scripts (`.py`, `.scala`, `.sql`), and text files (`.txt`, `.md`). CSV and binary data files are excluded — the goal is to understand *what people are working on*, not to index raw datasets.

```bash
python -m src.ingestion.cli --root dataset/ --mode full
```

Expected output:
```
Done — 5 workspaces, 211 artifacts (132 notebooks, 75 scripts, 4 text)
```

For subsequent runs, process only changed files:
```bash
python -m src.ingestion.cli --root dataset/ --mode incremental
```

### Step 4 — Start Milvus (vector database)

```bash
docker run -d \
  --name milvus \
  -p 19530:19530 \
  -p 9091:9091 \
  milvusdb/milvus:v2.6.14 standalone
```

Wait ~10 seconds, then verify:
```bash
docker logs milvus 2>&1 | tail -5
```

### Step 5 — Index workspace artifacts into Milvus

```bash
python -m src.retrieval.indexer \
  --catalog dataset/.ingestion/ingestion_catalog.json \
  --mode incremental
```

To fully rebuild from scratch:
```bash
python -m src.retrieval.indexer \
  --catalog dataset/.ingestion/ingestion_catalog.json \
  --mode full
```

### Step 6 — Generate and index artifact summaries

Artifact summaries are LLM-generated descriptions of each workspace artifact. They power the chatbot's artifact discovery capability and user profile generation.

```bash
python -m src.retrieval.artifact_summary_indexer \
  --catalog dataset/.ingestion/ingestion_catalog.json \
  --mode full
```

Or trigger via the API after the server is started:
```bash
curl -X POST "http://localhost:8000/admin/sync-artifact-summaries?force_full=true"
```

### Step 7 — Generate and index user profiles

User profiles summarise each workspace owner's areas of expertise. They are generated from artifact summaries and stored in the `user_profiles` Milvus collection.

```bash
# Requires artifact summaries to be indexed first (Step 6)
curl -X POST http://localhost:8000/admin/sync-profiles-from-summaries
```

### Step 8 — Ingest platform documentation for the chatbot

The AI chatbot answers questions about the platform using Word documents stored in `platform_documents/`. Place your `.docx` onboarding and how-to guides there, then run the ingestion:

```bash
# Add your Word documents to platform_documents/
ls platform_documents/
# Kubeflow_Access_Guide.docx  Kubeflow_First_Notebook.docx  Kubeflow_Spark_Job_Guide.docx ...
```

**Option A — via the API (recommended, after server is started):**
```bash
# Initial ingestion
curl -X POST http://localhost:8000/admin/ingest-docs

# Re-ingest and replace all existing chunks (e.g. after updating documents)
curl -X POST "http://localhost:8000/admin/ingest-docs?drop_existing=true"
```

**Option B — directly as a Python script:**
```bash
python -m src.retrieval.chatbot.doc_ingestion
```

What the ingestion pipeline does:
1. Reads every `.docx` file from `platform_documents/`
2. Extracts plain text from each document
3. Splits text into overlapping chunks (800 chars, 150-char overlap)
4. Embeds all chunks with OpenAI `text-embedding-3-small`
5. Stores chunks in the `platform_docs` Milvus collection

The chatbot is fully functional once Steps 6, 7, and 8 are complete.

### Step 9 — Start the retrieval API

```bash
python -m uvicorn src.retrieval.api:app --host 0.0.0.0 --port 8000
```

If port 8000 is in use:
```bash
python -m uvicorn src.retrieval.api:app --host 0.0.0.0 --port 8002
```

Verify health:
```bash
curl http://localhost:8000/health
```

Expected:
```json
{
  "status": "healthy",
  "vector_store": {"connected": true, "total_vectors": 190},
  "embedding_service": {"model_loaded": true, "model_name": "text-embedding-3-small"}
}
```

### Step 10 — Install webapp dependencies

```bash
cd webapp && npm install
```

### Step 11 — Start the webapp

```bash
cd webapp && npm run dev

# If your API is on a non-default port:
PYTHON_API_URL=http://localhost:8002 npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

The **AI Assistant** panel is accessible via the "AI Assistant" button in the header or the sidebar. It classifies queries and routes them to the correct knowledge source automatically.

---

## AI Chatbot

The chatbot is an enterprise knowledge assistant with three capabilities:

| Capability | Source | Example queries |
|---|---|---|
| **Documentation QA** | `platform_docs` (Word docs) | "How do I submit a Spark job?", "What is the onboarding process?" |
| **Artifact Discovery** | `artifact_summaries` | "Show me XGBoost notebooks", "Find Spark ETL scripts" |
| **User Discovery** | `user_profiles` | "Who works on NLP?", "Find experts in PySpark" |

The chatbot automatically classifies each query into one of four intents — `DOC_QA`, `ARTIFACT_SEARCH`, `USER_SEARCH`, or `HYBRID` — routes it to the correct retriever, and returns a structured, grounded response with source citations.

**Chat API:**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How do I access Kubeflow?",
    "history": []
  }'
```

Response schema:
```json
{
  "answer": "...",
  "intent": "DOC_QA",
  "confidence": 0.95,
  "artifacts": [{"title": "...", "reason": "...", "owner": "..."}],
  "users":     [{"name": "...", "reason": "...", "skills": ["..."]}],
  "sources":   [{"file": "Kubeflow_Access_Guide.docx", "doc_id": "kubeflow_access_guide"}]
}
```

All prompt templates are stored in `prompts/chatbot/` — no prompt text is hardcoded in Python source files.

---

## Python API Endpoints

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Vector store, embedding service, cache status |
| `GET` | `/metrics` | Uptime, query count, avg latency, memory usage |
| `GET` | `/docs` | Interactive OpenAPI documentation |

### Workspaces & Search

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/workspaces` | List all workspaces from the ingestion catalog |
| `GET` | `/workspaces/{id}` | Get a single workspace by ID |
| `POST` | `/query` | Semantic search across workspace artifacts |
| `GET` | `/profile/workspace/{id}` | AI-powered workspace profile |

### User Profiles

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/user-profiles` | List all user profiles |
| `GET` | `/user-profiles/{user_id}` | Get profile for a single user |

### Artifact Summaries

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/artifact-summaries?workspace_id=&artifact_id=` | Get one artifact summary |
| `GET` | `/artifact-summaries/workspace/{workspace_id}` | List all summaries for a workspace |

### Chatbot

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/chat` | Enterprise chatbot: classify → retrieve → generate |

### Admin

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/admin/sync` | Re-index workspace artifacts (`force_full: true` to rebuild) |
| `POST` | `/admin/sync-artifact-summaries` | Generate + index artifact summaries |
| `POST` | `/admin/sync-profiles` | Regenerate user profiles from raw catalog |
| `POST` | `/admin/sync-profiles-from-summaries` | Regenerate user profiles from artifact summaries (preferred) |
| `POST` | `/admin/ingest-docs` | Ingest Word docs from `platform_documents/` into `platform_docs` |

**`/admin/ingest-docs` query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `drop_existing` | bool | `false` | Drop and recreate the `platform_docs` collection before ingesting |

---

## Next.js API Routes (proxy layer)

| Webapp route | Proxies to |
|---|---|
| `GET /api/workspaces` | `GET /workspaces` |
| `GET /api/workspaces/[id]` | `GET /workspaces/{id}` |
| `GET /api/workspaces/[id]/profile` | `GET /profile/workspace/{id}` |
| `POST /api/search` | `POST /query` |
| `GET /api/health` | `GET /health` |
| `GET /api/metrics` | `GET /metrics` |
| `GET /api/user-profiles` | `GET /user-profiles` |
| `GET /api/user-profiles/[id]` | `GET /user-profiles/{id}` |
| `GET /api/artifact-summaries` | `GET /artifact-summaries` |
| `GET /api/artifact-summaries/workspace/[id]` | `GET /artifact-summaries/workspace/{id}` |
| `POST /api/chat` | `POST /chat` |
| `POST /api/admin/sync` | `POST /admin/sync` |
| `POST /api/admin/sync-profiles-from-summaries` | `POST /admin/sync-profiles-from-summaries` |
| `POST /api/admin/ingest-docs` | `POST /admin/ingest-docs` |

---

## Environment Variables

### Python backend (`.env` at project root)

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | **Required.** OpenAI API key for embeddings and LLM calls |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI embedding model |
| `EMBEDDING_DIMENSION` | `1536` | Must match the model's output dimension |
| `MILVUS_HOST` | `localhost` | Milvus server host |
| `MILVUS_PORT` | `19530` | Milvus server port |
| `MILVUS_COLLECTION` | `kubeflow_artifacts` | Primary artifact collection name |
| `INGESTION_CATALOG_PATH` | `dataset/.ingestion/ingestion_catalog.json` | Path to the ingestion catalog |
| `BATCH_SIZE` | `32` | Embeddings per OpenAI API request |
| `PROFILE_LLM_MODEL` | `gpt-4o-mini` | LLM model for profile generation and chatbot |

### Webapp (Next.js)

| Variable | Default | Description |
|----------|---------|-------------|
| `PYTHON_API_URL` | `http://localhost:8000` | Python backend URL (server-side only) |

Set in environment or create `webapp/.env.local`:
```bash
PYTHON_API_URL=http://localhost:8002
```

---

## Milvus Collections

| Collection | Description | Key fields |
|---|---|---|
| `kubeflow_artifacts` | Workspace artifact chunks | `artifact_id`, `workspace_id`, `content`, `vector` |
| `artifact_summaries` | LLM-generated artifact summaries | `user_id`, `artifact_id`, `artifact_summary`, `tags`, `vector` |
| `user_profiles` | LLM-generated user expertise profiles | `user_id`, `user_profile`, `tags`, `vector` |
| `platform_docs` | Platform documentation chunks (Word docs) | `doc_id`, `chunk_id`, `chunk_text`, `source_file`, `vector` |

---

## Prompt Templates

All LLM prompt templates are stored as plain text files in `prompts/` — no prompt text is hardcoded in Python source files.

```
prompts/
├── artifact_summary_prompt.txt          # Artifact summarisation
├── user_profile_prompt.txt              # User profile from raw catalog
├── user_profile_from_summaries_prompt.txt  # User profile from summaries
└── chatbot/
    ├── classifier/
    │   └── system.txt                   # Intent classification (DOC_QA / ARTIFACT_SEARCH / USER_SEARCH / HYBRID)
    ├── query_rewriter/
    │   └── system.txt                   # Semantic query optimisation
    ├── doc_qa/
    │   ├── system.txt                   # Platform expert persona + rules
    │   └── user.txt                     # Documentation context + question template
    ├── artifact_search/
    │   ├── system.txt                   # Artifact discovery persona + rules
    │   └── user.txt                     # Artifact results + query template
    ├── user_search/
    │   ├── system.txt                   # People-finder persona + rules
    │   └── user.txt                     # User profiles + query template
    └── hybrid/
        ├── system.txt                   # Multi-source persona + rules
        └── user.txt                     # All sources + query template
```

To update a prompt, edit the relevant `.txt` file — no code changes needed.

---

## Project Structure

```
project-1/
├── platform_documents/              # Word docs for chatbot Documentation QA
│   └── *.docx                       # Add onboarding + how-to guides here
├── prompts/                         # All LLM prompt templates (no prompts in code)
│   ├── artifact_summary_prompt.txt
│   ├── user_profile_prompt.txt
│   ├── user_profile_from_summaries_prompt.txt
│   └── chatbot/                     # Chatbot-specific prompts (one dir per component)
│       ├── classifier/system.txt
│       ├── query_rewriter/system.txt
│       ├── doc_qa/{system,user}.txt
│       ├── artifact_search/{system,user}.txt
│       ├── user_search/{system,user}.txt
│       └── hybrid/{system,user}.txt
├── dataset/                         # Sample Kubeflow workspace data
│   └── .ingestion/
│       ├── ingestion_catalog.json   # Generated by ingestion pipeline
│       └── ingestion_audit.json
├── src/
│   ├── ingestion/                   # Phase 1: data ingestion
│   │   ├── cli.py
│   │   ├── pipeline.py
│   │   ├── storage.py
│   │   ├── guards.py
│   │   ├── extractors.py
│   │   ├── models.py
│   │   └── utils.py
│   └── retrieval/                   # Phase 2–4: vector retrieval + LLM
│       ├── api.py                   # FastAPI application (all endpoints)
│       ├── config.py                # RetrievalConfig (env-driven)
│       ├── embeddings.py            # OpenAI embeddings + MD5 cache
│       ├── vector_store.py          # kubeflow_artifacts Milvus collection
│       ├── indexer.py               # CLI: embed + insert workspace artifacts
│       ├── retriever.py             # VectorRetriever + HybridRetriever
│       ├── document_loader.py
│       ├── document_guard.py
│       ├── text_processor.py
│       ├── profiling.py             # WorkspaceProfiler
│       ├── artifact_summary_store.py     # artifact_summaries collection
│       ├── artifact_summary_generator.py # LLM artifact summary generation
│       ├── artifact_summary_indexer.py   # CLI: generate + index summaries
│       ├── user_profile_store.py         # user_profiles collection
│       ├── user_profile_generator.py     # LLM user profile generation
│       ├── user_profile_from_summaries_generator.py
│       ├── profile_indexer.py            # CLI: generate + index profiles
│       ├── profile_from_summaries_indexer.py
│       └── chatbot/                 # Enterprise chatbot (Phase 4)
│           ├── __init__.py
│           ├── prompt_loader.py     # File-based prompt loader (lru_cache)
│           ├── classifier.py        # Intent classification
│           ├── query_rewriter.py    # Semantic query rewriting
│           ├── doc_store.py         # platform_docs Milvus collection
│           ├── doc_ingestion.py     # Word doc → chunks → embeddings → Milvus
│           ├── retrievers.py        # DocRetriever, ArtifactRetriever, UserRetriever
│           ├── prompts.py           # Prompt builder functions (load from files)
│           ├── formatter.py         # Output schema enforcer
│           └── engine.py            # ChatEngine orchestrator
├── webapp/                          # Phase 3: Next.js frontend
│   ├── app/
│   │   ├── api/                     # Server-side proxy routes
│   │   │   ├── chat/route.ts        # POST /api/chat
│   │   │   ├── workspaces/
│   │   │   ├── search/
│   │   │   ├── health/
│   │   │   ├── metrics/
│   │   │   ├── user-profiles/
│   │   │   ├── artifact-summaries/
│   │   │   └── admin/
│   │   │       ├── sync/
│   │   │       ├── ingest-docs/route.ts    # POST /api/admin/ingest-docs
│   │   │       └── sync-profiles-from-summaries/
│   │   ├── workspaces/
│   │   ├── search/
│   │   ├── user-profiles/
│   │   ├── analytics/
│   │   └── settings/
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AppShell.tsx         # Root layout with chat panel state
│   │   │   ├── sidebar.tsx          # Nav + AI Assistant toggle
│   │   │   └── header.tsx           # Header + AI Assistant toggle
│   │   ├── chatbot/
│   │   │   ├── ChatPanel.tsx        # Collapsible right-side chat panel
│   │   │   ├── ChatMessage.tsx      # Message bubble + intent badge + cards
│   │   │   └── ChatInput.tsx        # Auto-resizing textarea
│   │   ├── search/
│   │   ├── workspace/
│   │   └── ui/
│   ├── hooks/use-api.ts
│   ├── lib/api.ts
│   ├── types/index.ts
│   └── next.config.js
├── tests/
├── specs/
├── airflow/
├── requirements.txt
├── pyproject.toml
├── docker-compose.yml
├── docker-compose.airflow.yml
└── Dockerfile
```

---

## Testing

```bash
# All tests
python -m pytest tests/ -v

# Ingestion unit tests
python -m pytest tests/ingestion/unit/ -v

# Retrieval API tests
python -m pytest tests/test_retrieval_api.py -v
```

---

## Docker Deployment

```bash
docker compose up --build
```

- API: http://localhost:8000
- Webapp: http://localhost:3000

Run ingestion inside the container:
```bash
docker compose exec backend python -m src.ingestion.cli --root /data --mode full
```

---

## Airflow Orchestration

```bash
docker compose -f docker-compose.airflow.yml up --build
```

Airflow UI at http://localhost:8080 — credentials: `admin` / `admin`.

---

## Roadmap

- [x] Phase 1: Data Ingestion Pipeline
- [x] Phase 2: Vector Retrieval + FastAPI
- [x] Phase 3: Next.js Webapp Frontend
- [x] Phase 4: LLM artifact summaries + user profiles
- [x] Phase 4: Enterprise chatbot (doc QA, artifact discovery, user search)
- [ ] Phase 4: LiteLLM API Gateway
- [ ] Phase 4: Langfuse Observability
- [ ] Production deployment
