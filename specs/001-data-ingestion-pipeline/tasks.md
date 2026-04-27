# Tasks: Data Cleaning and Ingestion Pipeline

**Input**: Design documents from `specs/001-data-ingestion-pipeline/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`

## Phase 1: Setup (Shared Infrastructure)

- [X] T001 Create `src/ingestion` package with Python module files
- [X] T002 Create `tests/ingestion/unit` and `tests/ingestion/integration` directories
- [X] T003 [P] Add project dependency management and environment setup documentation in `specs/001-data-ingestion-pipeline/quickstart.md`
- [X] T004 [P] Define ingestion pipeline data models in `src/ingestion/models.py`
- [X] T005 [P] Create ingestion CLI entrypoint in `src/ingestion/cli.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

- [X] T006 Implement workspace discovery and workspace catalog abstractions in `src/ingestion/pipeline.py`
- [X] T007 [P] Implement metadata storage helper layer in `src/ingestion/storage.py`
- [X] T008 [P] Implement file classification and guardrail rules in `src/ingestion/guards.py`
- [X] T009 [P] Implement shared ingestion utilities in `src/ingestion/utils.py`
- [X] T010 Create `tests/ingestion/unit/test_models.py` for workspace and artifact model validation
- [X] T011 Create `tests/ingestion/unit/test_guards.py` for classification and sensitive-file decisions
- [X] T012 Create `tests/ingestion/unit/test_storage.py` for provenance and audit storage behavior

---

## Phase 3: User Story 1 - Workspace Source Ingestion (Priority: P1) 🎯 MVP

**Goal**: Discover workspaces, catalog file counts, and extract notebook metadata from supported artifacts.

**Independent Test**: Run the full ingestion pipeline against `dataset/` and verify workspace records, artifact records, and notebook metadata output.

- [X] T013 [US1] Implement workspace scanner in `src/ingestion/pipeline.py` to discover directories under `dataset/`
- [X] T014 [US1] Implement artifact ingestion flow in `src/ingestion/pipeline.py` for supported file types
- [X] T015 [US1] Implement notebook/script metadata extraction in `src/ingestion/extractors.py`
- [X] T016 [US1] Persist workspace, artifact, and notebook metadata records in `src/ingestion/storage.py`
- [X] T017 [US1] Create integration test `tests/ingestion/integration/test_full_ingestion.py` for sample `dataset/` workspaces
- [X] T018 [US1] Add validation in `src/ingestion/pipeline.py` that captures ingestion status and provenance for each workspace

---

## Phase 4: User Story 2 - Incremental Update and File Change Tracking (Priority: P2)

**Goal**: Enable the pipeline to reprocess only new or modified files and preserve unchanged records.

**Independent Test**: Modify or add workspace files, run incremental mode, and verify only changed artifacts are updated.

- [ ] T019 [US2] Implement content hashing or timestamp comparison in `src/ingestion/storage.py` for incremental detection
- [ ] T020 [US2] Add incremental ingestion logic in `src/ingestion/pipeline.py` with `--mode incremental`
- [ ] T021 [US2] Persist `ingestion_status` values `new`, `unchanged`, and `updated` in artifact records
- [ ] T022 [US2] Create integration test `tests/ingestion/integration/test_incremental_ingestion.py`
- [ ] T023 [US2] Document incremental execution semantics in `specs/001-data-ingestion-pipeline/quickstart.md`

---

## Phase 5: User Story 3 - Guardrail-aware Sanitization and Auditability (Priority: P3)

**Goal**: Detect sensitive and unsupported artifacts, skip or sanitize them, and record audit decisions.

**Independent Test**: Add sensitive or unsupported files to a workspace, run ingestion, and verify audit records describe the decision.

- [ ] T024 [US3] Identify sensitive/unsupported file patterns in `src/ingestion/guards.py`
- [ ] T025 [US3] Implement skip/sanitize behavior in `src/ingestion/pipeline.py` for guardrail decisions
- [ ] T026 [US3] Record guardrail audit events in `src/ingestion/storage.py`
- [ ] T027 [US3] Create integration test `tests/ingestion/integration/test_guardrail_audit.py`
- [ ] T028 [US3] Add a structured audit summary output for each ingestion run in `src/ingestion/pipeline.py`

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improve usability, documentation, monitoring readiness, and developer quality.

- [ ] T029 [P] Add structured ingestion run summaries and health flags in `src/ingestion/pipeline.py`
- [ ] T030 [P] Add linting/formatting guidance and dependency install notes in `specs/001-data-ingestion-pipeline/quickstart.md`
- [ ] T031 [P] Create a sample ingestion status API contract in `specs/001-data-ingestion-pipeline/contracts/ingestion-api.md`
- [ ] T032 [P] Review and finalize `specs/001-data-ingestion-pipeline/data-model.md` against implemented models
- [ ] T033 [P] Add or improve unit tests for helper logic in `tests/ingestion/unit`

---

## Dependencies & Execution Order

- Setup (Phase 1) must complete before Foundational work begins.
- Foundational (Phase 2) blocks all user story implementation.
- User Story 1 (Phase 3) is the MVP and should be completed first.
- User Story 2 and User Story 3 can proceed after foundational work and may overlap once Phase 2 is complete.
- Polish Phase depends on completion of all user story phases.

## Parallel Execution Examples

- [P] tasks can be worked in parallel when they touch separate modules or tests.
- Example parallel work:
  - `T007 [P]`, `T008 [P]`, and `T009 [P]` can be implemented together after `T006`.
  - `T010`, `T011`, and `T012` can be authored in parallel with foundational code.
  - `T019 [US2]` and `T024 [US3]` can begin once foundational ingestion flow exists.

## Implementation Strategy

### MVP first
1. Complete Phase 1 setup file structure.
2. Complete Phase 2 foundational storage, guardrails, and shared utilities.
3. Implement User Story 1 in Phase 3 and verify with full ingestion integration tests.
4. Expand to User Story 2 and User Story 3 only after the core ingestion flow is stable.
5. Finish polish tasks and ensure the pipeline is documented and test-covered.
