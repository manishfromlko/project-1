# API Contract: Ingestion Control and Status

This contract defines the external interface for controlling ingestion and checking pipeline state.

## POST /api/ingestion/run

Start an ingestion job.

### Request
- `mode` (string, required): `full` or `incremental`
- `workspace_ids` (array<string>, optional): list of workspaces to process; if omitted, process all workspaces.
- `dry_run` (boolean, optional): if true, validate the run without persisting new ingestion state.

### Response
- `run_id` (string): unique identifier for the ingestion execution.
- `started_at` (string, datetime)
- `mode` (string)
- `workspace_scope` (array<string>|string)
- `status` (string): `running`, `accepted`, `failed`
- `message` (string|null)

## GET /api/ingestion/status

Retrieve the most recent ingestion health summary.

### Response
- `latest_run` (object): summary of the latest ingestion execution.
- `workspaces_processed` (integer)
- `files_processed` (integer)
- `errors` (integer)
- `skipped_artifacts` (integer)
- `last_success_at` (string, datetime|null)
- `pipeline_health` (string): `ok`, `degraded`, `failed`

## GET /api/ingestion/workspaces

List ingested workspaces and status.

### Response
- `workspaces` (array<object>)
  - `workspace_id` (string)
  - `owner` (string)
  - `file_count` (integer)
  - `last_ingested_at` (string, datetime|null)
  - `status` (string)

## GET /api/ingestion/workspace/{workspace_id}/artifacts

List ingested artifacts for a given workspace.

### Response
- `workspace_id` (string)
- `artifacts` (array<object>)
  - `artifact_id` (string)
  - `relative_path` (string)
  - `file_type` (string)
  - `size_bytes` (integer)
  - `ingestion_status` (string)
  - `classification` (object)

## GET /api/ingestion/run/{run_id}

Retrieve a single run’s details and validation output.

### Response
- `run_id` (string)
- `started_at` (string)
- `completed_at` (string|null)
- `run_type` (string)
- `status` (string)
- `summary` (object)
- `validation` (object)
- `audit_records` (array<object>)
