# Data Model: Data Cleaning and Ingestion Pipeline

## Entities

### Workspace
- `workspace_id` (string): unique identifier, typically the workspace folder name / corp ID.
- `owner` (string): normalized user identity.
- `root_path` (string): absolute or canonical path to the workspace directory.
- `file_count` (integer): total count of supported files discovered.
- `last_ingested_at` (datetime): timestamp of last successful ingestion run.
- `status` (enum): `pending`, `success`, `partial`, `failed`.
- `source_coverage` (object): counts by category, e.g. notebooks, scripts, binaries, unsupported.
- `notes` (string|null): optional ingestion remarks.

### FileArtifact
- `artifact_id` (string): stable identifier, e.g. hash of workspace + relative path.
- `workspace_id` (string): foreign key to `Workspace`.
- `relative_path` (string): path within the workspace.
- `file_name` (string)
- `file_type` (enum): `notebook`, `script`, `text`, `document`, `binary`, `image`, `archive`, `env`, `unsupported`.
- `mime_type` (string|null)
- `size_bytes` (integer)
- `last_modified_at` (datetime)
- `ingestion_status` (enum): `new`, `unchanged`, `updated`, `skipped`, `error`.
- `classification` (object): extracted categories such as `sensitive`, `processable`, `metadata-only`.
- `content_hash` (string|null): content fingerprint for incremental detection.
- `capture_source` (object): evidence of ingestion origin, including raw path and source identifier.

### NotebookDocument
- `document_id` (string): stable ID for notebook or notebook-like artifact.
- `artifact_id` (string): foreign key to `FileArtifact`.
- `notebook_title` (string|null)
- `kernel_language` (string|null)
- `cells_count` (integer|null)
- `extracted_tools` (array<string>): libraries and frameworks detected (e.g. `pyspark`, `kafka`, `postgres`, `redis`).
- `database_targets` (array<string>): database names, schemas, or connection strings identified.
- `table_references` (array<string>): candidate tables mentioned in code or SQL statements.
- `notebook_summary` (string|null): high-level extracted description from the source for internal validation.
- `source_snippets` (array<object>): selected evidence snippets with line/cell references.

### IngestionRun
- `run_id` (string): unique execution identifier.
- `started_at` (datetime)
- `completed_at` (datetime|null)
- `run_type` (enum): `initial`, `incremental`, `retry`.
- `workspace_scope` (array<string>|null): list of targeted workspace IDs or `all`.
- `status` (enum): `running`, `success`, `partial`, `failed`.
- `summary` (object): counts of workspaces touched, files processed, errors, skipped artifacts.
- `validation` (object): ingestion-level validation flags and guardrail outcomes.

### IngestionAudit
- `audit_id` (string)
- `artifact_id` (string|null)
- `workspace_id` (string|null)
- `run_id` (string)
- `decision` (enum): `ingested`, `skipped`, `sanitized`, `error`.
- `reason` (string): explanation for the decision.
- `matched_pattern` (string|null): sensitive or unsupported pattern label.
- `metadata_snapshot` (object|null): captured artifact metadata at decision time.

## Relationships
- `Workspace` 1 → N `FileArtifact`
- `FileArtifact` 1 → 1 `NotebookDocument` (for notebook-like artifacts)
- `IngestionRun` 1 → N `IngestionAudit`
- `Workspace` 1 → N `IngestionAudit`

## Validation rules
- Workspace IDs MUST be derived consistently from workspace folder names and normalized to lowercase.
- File hashing for incremental detection MUST use a stable fingerprint algorithm and exclude unsupported binary-only metadata if the file is skipped.
- NotebookDocument extraction MUST only occur for `notebook`, `script`, and `text` artifact types.
- Guardrail decisions MUST never mark sensitive content as `ingested` without an explicit sanitization record.
