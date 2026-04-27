# Quickstart: Data Cleaning and Ingestion Pipeline

## Prerequisites

- Python 3.11+
- `pip` or equivalent package manager
- Access to the source workspace tree mounted locally under `dataset/`
- A shell session opened in the repository root: `/Users/manish/mount/projects/project-1`

## Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install langchain litellm pymilvus pydantic pytest
```

> Note: The initial ingestion pipeline is backend-first. Additional dependencies for Langfuse, Milvus, and frontend UI are added later when retrieval and generation features are implemented.

## Run initial ingestion

```bash
python -m src.ingestion.cli --root dataset/ --mode full
```

## Run incremental update

```bash
python -m src.ingestion.cli --root dataset/ --mode incremental
```

## Validate output

- Confirm that a workspace catalog was created for each directory under `dataset/`.
- Verify that metadata records contain `file_count`, `last_ingested_at`, and a `status`.
- Check that notebook extraction recorded `extracted_tools`, `database_targets`, and `table_references`.
- Review the audit log for any `skipped` or `sanitized` decisions.

## Next step

After the ingestion pipeline is working, the next feature is the retriever stage. That stage will consume the cleaned metadata output and populate the notebook-level and user-level Milvus collections.
