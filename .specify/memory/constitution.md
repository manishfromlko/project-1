<!--
Sync Impact Report
Version change: template → 1.0.0
Modified principles:
  - placeholder principle 1 → I. Data-First Visibility
  - placeholder principle 2 → II. Workspace-Level Accountability
  - placeholder principle 3 → III. Dual-Collection Representation
  - placeholder principle 4 → IV. Guardrails and Responsible Generation
  - placeholder principle 5 → V. Observability, Evaluation, and Incremental Delivery
Added sections:
  - Security & Compliance
  - Development Workflow
Removed sections:
  - none
Templates reviewed:
  - .specify/templates/plan-template.md ✅
  - .specify/templates/spec-template.md ✅
  - .specify/templates/tasks-template.md ✅
  - .specify/templates/constitution-template.md ✅
Follow-up TODOs: none
-->

# Kubeflow Workspace Profiling Constitution

## Core Principles

### I. Data-First Visibility
- All profiling artifacts MUST begin with a deterministic, audit-ready ingestion model of user workspace content.
- Ingestion MUST extract file inventory, notebook metadata, query targets, and tool usage from source workspaces before any summary generation.
- Rationale: Accurate management visibility depends on source evidence and structured provenance, not only on later LLM narrative output.

### II. Workspace-Level Accountability
- Each corpus MUST be organized around workspace identity and incremental file counts; user profiles MUST reflect workspace owner and workspace activity.
- The user panel MUST sort by active workspace file count and expose per-workspace metrics such as last ingestion time and file coverage.
- Rationale: Management requires a stable link between users, their NAS workspace, and the work artifacts they generate.

### III. Dual-Collection Representation
- The system MUST use separate Milvus collections for user-level profiles and notebook-level / document-level embeddings.
- Notebook-level records MUST preserve source path, notebook title, tooling/database mentions, and extraction timestamp.
- User-profile records MUST aggregate high-level themes, common tools/databases, and scored relevance from the aggregated document set.
- Rationale: Dual collections ensure precise retrieval for both top-level profile queries and detailed notebook summaries.

### IV. Guardrails and Responsible Generation
- All generated summaries and labels MUST be supported by explicit source citations and must expose uncertainty where support is incomplete.
- The system MUST enforce validation before UI delivery, with generated content flagged when evidence is weak or the source is unavailable.
- Rationale: Guardrails preserve trust in sensitive profiling outputs and prevent hallucinated claims about user activity.

### V. Observability, Evaluation, and Incremental Delivery
- Monitoring MUST cover ingestion health, vector store freshness, retrieval latency, generation quality, and guardrail failures.
- Evaluation MUST measure profile accuracy against workspace-derived signals and surface drift when source coverage or data patterns change.
- Rationale: Continuous observability and evaluation ensure the profiler remains reliable as notebooks, environments, and tooling evolve.

## Security & Compliance
- Access to workspace sources and profiling outputs MUST be limited to authorized roles and audited per request.
- Sensitive files such as credentials, environment definitions, and private model artifacts MUST NOT be ingested unless explicitly allowed and sanitized.
- Data retention, deletion, and escalation policies MUST be documented for NAS workspaces, generated profiles, and derived embeddings.
- Rationale: User workspace profiling touches sensitive analytics pipelines and corporate data, so security and compliance are foundational.

## Development Workflow
- The project MUST define versioned API contracts, scheduled ingestion jobs, and a clear review path for changes to ingestion, retrieval, generation, evaluation, or monitoring.
- Each new feature MUST be scoped as either ingestion, retrieval, generation, evaluation, or monitoring work.
- Code reviews MUST verify that changes preserve the separation between user-level profiles and notebook-level document collections.
- Rationale: Explicit workflow boundaries make this hybrid data + AI product easier to maintain, audit, and evolve safely.

## Governance
- This constitution governs architecture, data handling, and release discipline for the Kubeflow Workspace Profiling project.
- Amendments require a written proposal, review by at least one data platform owner and one security reviewer, and a documented migration plan.
- Versioning uses semantic versioning: major for principle or governance changes, minor for new sections or material additions, patch for wording clarifications.
- Compliance reviews MUST occur whenever a new collection type, data source, or model endpoint is added.

**Version**: 1.0.0 | **Ratified**: 2026-04-28 | **Last Amended**: 2026-04-28

