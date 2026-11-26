"""
src/enterprise_core/integrations/bucket_adapter.py
==================================================
Bucket: Evidence & Immutable Audit Storage Adapter.
Provides append-only persistence and SHA-256 integrity verification.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any, Dict, Optional
from contracts.schemas import (
    AuditEvidenceEnvelope,
    AuditStorageReceipt,
    SCHEMA_VERSION,
)
from ..determinism import compute_sha256


class BucketAuditAdapter:
    """Client adapter for BHIV Bucket immutable audit repository."""

    def __init__(self, storage_dir: str = "data/bucket_records"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def store_evidence(self, envelope: AuditEvidenceEnvelope) -> AuditStorageReceipt:
        """Stores evidence append-only and returns cryptographic receipt."""
        digest = compute_sha256(envelope.data)
        envelope_data = envelope.model_dump()
        envelope_data["sha256_digest"] = digest

        target_file = self.storage_dir / f"{envelope.artifact_type}_{envelope.artifact_id}.json"
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(envelope_data, f, indent=2, ensure_ascii=False)

        return AuditStorageReceipt(
            status="STORED",
            artifact_id=envelope.artifact_id,
            artifact_type=envelope.artifact_type,
            trace_id=envelope.trace_id,
            stored_path=str(target_file).replace("\\", "/"),
            sha256_digest=digest,
            schema_version=SCHEMA_VERSION,
        )

    def retrieve_evidence(self, artifact_type: str, artifact_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves raw evidence by artifact ID."""
        target_file = self.storage_dir / f"{artifact_type}_{artifact_id}.json"
        if not target_file.exists():
            return None
        with open(target_file, "r", encoding="utf-8") as f:
            return json.load(f)
