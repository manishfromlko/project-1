from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Dict, Iterable, Optional

from .extractors import extract_metadata_from_notebook, extract_metadata_from_script
from .guards import classify_file
from .models import (
    FileArtifact,
    IngestionAudit,
    IngestionRun,
    IngestionStatus,
    FileType,
    Workspace,
)
from .storage import Storage
from .utils import compute_file_hash, normalize_workspace_id, safe_list_dir


SUPPORTED_EXTENSIONS = {
    ".ipynb": FileType.NOTEBOOK,
    ".py": FileType.SCRIPT,
    ".scala": FileType.SCRIPT,
    ".sql": FileType.SCRIPT,
    ".txt": FileType.TEXT,
    ".csv": FileType.TEXT,
    ".tsv": FileType.TEXT,
    ".docx": FileType.DOCUMENT,
}


class IngestionPipeline:
    def __init__(self, root_path: str, mode: str = "full", dry_run: bool = False):
        self.root = Path(root_path)
        self.mode = mode
        self.dry_run = dry_run
        self.ingestion_run = IngestionRun(
            run_id=f"run_{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            started_at=datetime.datetime.utcnow(),
            run_type="initial" if mode == "full" else "incremental",
        )
        self.storage = Storage(self.root / ".ingestion")

    def run(self) -> None:
        self.ingestion_run.workspace_scope = [p.name for p in safe_list_dir(self.root) if p.is_dir()]
        self.ingestion_run.status = "running"
        for workspace_dir in self._list_workspaces():
            workspace = self._ingest_workspace(workspace_dir)
            self.storage.write_workspace(workspace)
        self.ingestion_run.completed_at = datetime.datetime.utcnow()
        self.ingestion_run.status = "success"
        if not self.dry_run:
            self.storage.save()

    def _list_workspaces(self) -> Iterable[Path]:
        return [path for path in safe_list_dir(self.root) if path.is_dir()]

    def _ingest_workspace(self, workspace_dir: Path) -> Workspace:
        workspace_id = normalize_workspace_id(workspace_dir.name)
        workspace = Workspace(
            workspace_id=workspace_id,
            owner=workspace_id,
            root_path=str(workspace_dir.resolve()),
        )
        artifacts = self._scan_files(workspace_dir, workspace_id)
        workspace.file_count = len(artifacts)
        workspace.source_coverage = self._summarize_coverage(artifacts)
        workspace.last_ingested_at = datetime.datetime.utcnow()
        workspace.status = "success"
        return workspace

    def _scan_files(self, workspace_dir: Path, workspace_id: str) -> Iterable[FileArtifact]:
        artifacts = []
        for path in workspace_dir.rglob("*"):
            if path.is_dir():
                continue
            classification = classify_file(path)
            file_type = SUPPORTED_EXTENSIONS.get(path.suffix.lower(), FileType.UNSUPPORTED)
            artifact = FileArtifact(
                artifact_id=f"{workspace_id}:{path.relative_to(workspace_dir)}",
                workspace_id=workspace_id,
                relative_path=str(path.relative_to(workspace_dir)),
                file_name=path.name,
                file_type=file_type,
                mime_type=None,
                size_bytes=path.stat().st_size,
                last_modified_at=datetime.datetime.fromtimestamp(path.stat().st_mtime),
                ingestion_status=IngestionStatus.SKIPPED
                if classification["decision"] == "skipped"
                else IngestionStatus.NEW,
                classification={
                    "decision": classification["decision"],
                    "matched_pattern": classification["matched_pattern"],
                    "category": classification["classification"],
                },
                content_hash=compute_file_hash(path),
                capture_source={"source_path": str(path.resolve())},
            )

            if classification["decision"] == "skipped":
                audit = IngestionAudit(
                    audit_id=f"audit_{workspace_id}:{artifact.relative_path}",
                    artifact_id=artifact.artifact_id,
                    workspace_id=workspace_id,
                    run_id=self.ingestion_run.run_id,
                    decision="skipped",
                    reason="guardrail detected sensitive or unsupported artifact",
                    matched_pattern=classification["matched_pattern"],
                    metadata_snapshot={
                        "relative_path": artifact.relative_path,
                        "file_type": file_type.value,
                        "size_bytes": artifact.size_bytes,
                    },
                )
                self.storage.write_audit(audit)
                self.storage.write_artifact(artifact)
                continue

            if file_type == FileType.NOTEBOOK:
                metadata = extract_metadata_from_notebook(path)
            elif file_type == FileType.SCRIPT:
                metadata = extract_metadata_from_script(path)
            else:
                metadata = {}

            if metadata:
                artifact.classification["metadata"] = {
                    "tools": metadata.get("extracted_tools", []),
                    "databases": metadata.get("database_targets", []),
                    "tables": metadata.get("table_references", []),
                }
            self.storage.write_artifact(artifact)
            artifacts.append(artifact)
        return artifacts

    def _summarize_coverage(self, artifacts: Iterable[FileArtifact]) -> Dict[str, int]:
        coverage: Dict[str, int] = {}
        for artifact in artifacts:
            category = artifact.classification.get("category", "unknown")
            coverage[category] = coverage.get(category, 0) + 1
        return coverage
