# Kubeflow Workspace Profiling Webapp

A generative AI-powered web application for profiling and analyzing Kubeflow workspaces. Provides intelligent insights into data science workflows, ML pipelines, and collaboration patterns through automated data ingestion, vector search, and LLM-powered analysis.

## Architecture Overview

The system is built in four phases, each building on the previous:

```
Phase 1: Data Ingestion   →  dataset/.ingestion/ingestion_catalog.json
Phase 2: Vector Retrieval →  Milvus (port 19530) + FastAPI (port 8000)
Phase 3: Webapp Frontend  →  Next.js (port 3000)
Phase 4: LLM Generation   →  LiteLLM + Langfuse (upcoming)
```

## Prerequisites

- Python 3.11+
- Docker (for Milvus vector database)
- Node.js 18+ (for webapp only)

---

## Step-by-Step: Running the Full Stack

### Step 1 — Create and activate a virtual environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

### Step 2 — Install Python dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> **Note on version pins:** `sentence-transformers<3`, `transformers<5`, and `numpy<2` are pinned
> because torch 2.2.x (the version installed by sentence-transformers 2.x) is incompatible with
> numpy 2.x (causes `_ARRAY_API not found` crash) and with transformers 5.x (causes `NameError: name 'nn' is not defined`).

### Step 3 — Run the data ingestion pipeline

```bash
python -m src.ingestion.cli --root dataset/ --mode full
```

Expected output:
```
Ingestion complete: 4 workspaces, 178 artifacts
Catalog written to: dataset/.ingestion/ingestion_catalog.json
```

For subsequent runs, use incremental mode to process only changed files:

```bash
python -m src.ingestion.cli --root dataset/ --mode incremental
```

Dry run (validate without writing):

```bash
python -m src.ingestion.cli --root dataset/ --mode full --dry-run
```

### Step 4 — Start Milvus (vector database)

```bash
docker run -d \
  --name milvus \
  -p 19530:19530 \
  -p 9091:9091 \
  milvusdb/milvus:v2.6.14 standalone
```

Wait ~10 seconds for Milvus to be ready, then verify:

```bash
docker logs milvus 2>&1 | tail -5
```

### Step 5 — Populate the vector store

This step loads documents from the ingestion catalog, generates embeddings, and inserts them into Milvus. Run once (or after re-ingestion to refresh):

```bash
INGESTION_CATALOG_PATH=dataset/.ingestion/ingestion_catalog.json python -c "
from src.retrieval.config import RetrievalConfig
from src.retrieval.document_loader import DocumentLoader
from src.retrieval.embeddings import EmbeddingService
from src.retrieval.vector_store import VectorStore

config = RetrievalConfig.from_env()

store = VectorStore(config)
store.create_collection()

loader = DocumentLoader('dataset/.ingestion/ingestion_catalog.json', config)
documents = loader.load_documents()

embedder = EmbeddingService(config)
texts = [doc.page_content for doc in documents]
embeddings = embedder.generate_embeddings(texts)

artifact_ids = [doc.metadata.get('artifact_id', '') for doc in documents]
contents = [doc.page_content[:5000] for doc in documents]
metadatas = [doc.metadata for doc in documents]

store.insert_vectors(artifact_ids, embeddings, contents, metadatas)
print(f'Inserted {len(documents)} vectors into Milvus')
"
```

Expected output:
```
Loaded 301 documents from 178 artifacts
Applied guardrails: 298/301 documents retained
Inserted 298 vectors into Milvus
```

### Step 6 — Start the retrieval API

```bash
INGESTION_CATALOG_PATH=dataset/.ingestion/ingestion_catalog.json \
  python -m uvicorn src.retrieval.api:app --host 0.0.0.0 --port 8000
```

> **Important:** Always use `python -m uvicorn` (not bare `uvicorn`) so it uses the active venv.
> Run this from the project root, not from inside `src/retrieval/`.

Verify the API is healthy:

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "vector_store": {"connected": true, "total_vectors": 298},
  "embedding_service": {"model_loaded": true, "model_name": "all-MiniLM-L6-v2"}
}
```

### Step 7 — Test semantic search

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "machine learning with pyspark", "top_k": 3}'
```

Expected: 3 results with cosine similarity scores (~0.6–0.7), artifact IDs, and content snippets.

### Step 8 — Start the webapp (optional)

```bash
cd webapp
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

> The webapp expects the API at `http://localhost:8000`. If you used a different port, set:
> ```bash
> export NEXT_PUBLIC_API_URL=http://localhost:8000
> ```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | System health: vector store, embedding service, cache |
| `GET` | `/metrics` | Uptime, query count, avg latency, memory usage |
| `POST` | `/query` | Semantic search across workspace artifacts |
| `GET` | `/profile/workspace/{workspace_id}` | AI-powered workspace insights |
| `POST` | `/admin/sync` | Trigger re-sync with ingestion catalog |
| `GET` | `/docs` | Interactive OpenAPI documentation |

### Query request body

```json
{
  "query": "neural network classification",
  "top_k": 10,
  "workspace_ids": ["ajay11.yadav"],
  "use_hybrid": false
}
```

Set `use_hybrid: true` to combine vector similarity with keyword matching.

### Example: workspace profile

```bash
curl http://localhost:8000/profile/workspace/ajay11.yadav
```

Returns tool usage (pandas, sklearn, spark), topic analysis (ML, NLP, clustering), collaboration patterns, and code metrics.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MILVUS_HOST` | `localhost` | Milvus server host |
| `MILVUS_PORT` | `19530` | Milvus server port |
| `MILVUS_COLLECTION` | `kubeflow_artifacts` | Collection name |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | SentenceTransformer model |
| `INGESTION_CATALOG_PATH` | `./data/catalog.json` | Path to ingestion catalog JSON |
| `BATCH_SIZE` | `32` | Embedding batch size |

---

## Project Structure

```
project-1/
├── dataset/                         # Sample Kubeflow workspace data
│   └── .ingestion/                  # Generated by ingestion pipeline
│       ├── ingestion_catalog.json   # Workspace + artifact metadata
│       └── ingestion_audit.json     # Guardrail audit log
├── src/
│   ├── ingestion/                   # Phase 1: data ingestion
│   │   ├── cli.py                   # Entry point (python -m src.ingestion.cli)
│   │   ├── pipeline.py              # Discovery, classification, extraction
│   │   ├── storage.py               # JSON catalog persistence
│   │   ├── guards.py                # Sensitive file detection
│   │   ├── extractors.py            # Notebook and script metadata
│   │   ├── models.py                # Dataclasses: Workspace, FileArtifact, etc.
│   │   └── utils.py                 # SHA256 hashing, safe I/O
│   └── retrieval/                   # Phase 2: vector retrieval
│       ├── api.py                   # FastAPI application
│       ├── config.py                # RetrievalConfig (env-driven)
│       ├── embeddings.py            # SentenceTransformer + MD5 cache
│       ├── vector_store.py          # Milvus HNSW collection (384-dim)
│       ├── document_loader.py       # Catalog → LangChain Documents
│       ├── document_guard.py        # Document-level content filtering
│       ├── retriever.py             # VectorRetriever + HybridRetriever
│       ├── text_processor.py        # Text chunking
│       └── profiling.py             # WorkspaceProfiler
├── webapp/                          # Phase 3: Next.js frontend
├── tests/
│   ├── ingestion/unit/
│   ├── ingestion/integration/
│   └── test_retrieval_api.py
├── specs/                           # Feature specifications and plans
├── airflow/                         # Airflow DAG for scheduled ingestion
├── requirements.txt                 # Python dependencies (version-pinned)
├── docker-compose.yml               # Full stack: API + webapp + Milvus
├── docker-compose.airflow.yml       # Airflow orchestration stack
└── Dockerfile                       # Backend container
```

---

## Testing

```bash
# All tests
python -m pytest tests/ -v

# Ingestion unit tests only
python -m pytest tests/ingestion/unit/ -v

# Ingestion integration tests
python -m pytest tests/ingestion/integration/ -v

# Retrieval API tests
python -m pytest tests/test_retrieval_api.py -v
```

---

## Docker Deployment

Build and run the full stack (API + webapp + Milvus):

```bash
docker compose up --build
```

- API: http://localhost:8000
- Webapp: http://localhost:3000

Run ingestion inside the backend container:

```bash
docker compose exec backend python -m src.ingestion.cli --root /data --mode full
```

---

## Airflow Orchestration

Airflow configuration is at `docker-compose.airflow.yml`. The DAG at `airflow/dags/ingestion_dag.py` runs the ingestion pipeline on a schedule.

```bash
docker compose -f docker-compose.airflow.yml up --build
```

Airflow UI at http://localhost:8080 — credentials: `admin` / `admin`.

---

## Roadmap

- [x] Phase 1: Data Ingestion Pipeline
- [x] Phase 2: Vector Retrieval + FastAPI
- [x] Phase 3: Next.js Webapp Frontend
- [ ] Phase 4: LiteLLM API Gateway
- [ ] Phase 4: Langfuse Observability
- [ ] Production deployment
