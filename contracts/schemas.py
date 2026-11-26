"""
contracts/schemas.py
====================
SETU OS Architecture v6.0 - Canonical Interface Schemas (v1.0)
Target Product: BHIV Enterprise Operating System Common Core (BHIV)
Task ID: T-OUT-OF-SYLLABUS

Governing Integration Block:
- BHIV Enterprise Operating System Common Core
- GC Shakti (Governance Intelligence & Policy Authority)
- Niyantran (Task Assignment & Workflow Lifecycle Engine)
- Bucket (Evidence & Immutable Audit Storage)
- Gov-OS (Governance Ledger & Cryptographic Verification)
- Saarthi (Visibility Layer & Operational Oversight)
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

SCHEMA_VERSION: str = "1.0.0"


class WorkflowStateEnum(str, Enum):
    """Deterministic finite state machine stages for BHIV Enterprise Core."""
    INTAKE = "INTAKE"
    POLICY_VALIDATION = "POLICY_VALIDATION"
    EVALUATION_PENDING = "EVALUATION_PENDING"
    AWAITING_REVIEW = "AWAITING_REVIEW"
    GOVERNED_APPROVAL = "GOVERNED_APPROVAL"
    REJECTED = "REJECTED"
    NIYANTRAN_DISPATCH = "NIYANTRAN_DISPATCH"
    COMMITTED = "COMMITTED"


class PolicyStatusEnum(str, Enum):
    """GC Shakti evaluation outcomes."""
    PASS = "PASS"
    FAIL = "FAIL"
    CONDITIONAL = "CONDITIONAL"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


# -----------------------------------------------------------------------------
# Base Schema Configuration: Strict Mode (extra forbidden, strict types)
# -----------------------------------------------------------------------------
class StrictBaseModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=False,
        validate_assignment=True,
        str_strip_whitespace=True,
    )


# -----------------------------------------------------------------------------
# 1. GC Shakti: Governance Intelligence & Policy Authority Contracts
# -----------------------------------------------------------------------------
class PolicyEvaluationRequest(StrictBaseModel):
    """Inbound request to GC Shakti Policy Engine."""
    policy_id: str = Field(..., min_length=3, max_length=64, description="Canonical policy identifier (e.g. POL-MKT-001)")
    actor_id: str = Field(..., min_length=2, max_length=128, description="Identifier of the executing actor or candidate")
    actor_role: str = Field(..., min_length=2, max_length=64, description="Designated role (e.g. 'Product Owner', 'Reviewer')")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Operational parameters for policy evaluation")
    context_tags: List[str] = Field(default_factory=list, description="Categorization tags")


class PolicyEvaluationResult(StrictBaseModel):
    """Outbound evaluation verdict from GC Shakti."""
    policy_id: str
    status: PolicyStatusEnum
    compliance_score: float = Field(..., ge=0.0, le=100.0)
    violations: List[str] = Field(default_factory=list)
    citations: List[str] = Field(default_factory=list)
    condition_notes: Optional[str] = None
    evaluated_by: str = "GC_SHAKTI_V6"
    schema_version: str = SCHEMA_VERSION


# -----------------------------------------------------------------------------
# 2. Niyantran: Task Assignment & Workflow Lifecycle Engine Contracts
# -----------------------------------------------------------------------------
class TaskAssignmentRequest(StrictBaseModel):
    """Inbound assignment order dispatched through Niyantran."""
    task_id: str = Field(..., min_length=3, max_length=64, description="Canonical Task ID, e.g. T-OUT-OF-SYLLABUS")
    target_agent: str = Field(..., min_length=2, max_length=128, description="Assigned candidate or autonomous agent")
    title: str = Field(..., min_length=5, max_length=256, description="Human readable canonical task title")
    priority: str = Field("HIGH", pattern="^(CRITICAL|HIGH|MEDIUM|LOW)$")
    calibrated_duration_mins: int = Field(..., ge=15, le=1440, description="Allocated shift duration (e.g. 180-360 mins)")
    spec_payload: Dict[str, Any] = Field(..., description="Canonical depth specification without placeholders")
    assigned_by: str = Field(..., min_length=2, max_length=128, description="Authorized human reviewer or Parikshak engine")

    @field_validator("task_id")
    @classmethod
    def validate_task_id_format(cls, v: str) -> str:
        if not re.match(r"^[A-Za-z0-9_\-]+$", v):
            raise ValueError("task_id must contain only alphanumeric characters, underscores, or hyphens")
        return v


class TaskAssignmentResponse(StrictBaseModel):
    """Niyantran assignment confirmation receipt."""
    assignment_id: str
    task_id: str
    target_agent: str
    status: str = "ASSIGNED"
    dispatched_at: str
    trace_id: str
    schema_version: str = SCHEMA_VERSION


# -----------------------------------------------------------------------------
# 3. Bucket: Evidence & Immutable Audit Storage Contracts
# -----------------------------------------------------------------------------
class AuditEvidenceEnvelope(StrictBaseModel):
    """Immutable evidence envelope stored into BHIV Bucket."""
    artifact_id: str = Field(..., min_length=3, max_length=128)
    artifact_type: str = Field(..., pattern="^(telemetry|instruction|blueprint|contract|authority|gate|execution|result|alert|review_evidence)$")
    trace_id: str = Field(..., min_length=8, max_length=128)
    timestamp: str
    data: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    sha256_digest: Optional[str] = None


class AuditStorageReceipt(StrictBaseModel):
    """Bucket receipt confirming append-only persistence."""
    status: str = "STORED"
    artifact_id: str
    artifact_type: str
    trace_id: str
    stored_path: str
    sha256_digest: str
    schema_version: str = SCHEMA_VERSION


# -----------------------------------------------------------------------------
# 4. Gov-OS: Governance Ledger & Cryptographic Verification Contracts
# -----------------------------------------------------------------------------
class GovernanceLedgerEntry(StrictBaseModel):
    """Gov-OS immutable ledger block recording state transition attestation."""
    block_index: int = Field(..., ge=0)
    transaction_id: str
    trace_id: str
    task_id: str
    state_hash: str = Field(..., min_length=64, max_length=64, description="Canonical SHA-256 state digest")
    previous_hash: str = Field(..., min_length=64, max_length=64)
    timestamp: str
    recorded_by: str = "GOV_OS_CORE_V6"
    status: str = "COMMITTED"
    schema_version: str = SCHEMA_VERSION


class CryptographicVerification(StrictBaseModel):
    """Gov-OS cryptographic proof report."""
    is_valid: bool
    state_hash: str
    algorithm: str = "SHA-256"
    verified_at: str
    ledger_block_index: int


# -----------------------------------------------------------------------------
# 5. Saarthi: Operational Visibility & Oversight Contracts
# -----------------------------------------------------------------------------
class SaarthiTelemetryEvent(StrictBaseModel):
    """Live telemetry stream event emitted to Saarthi dashboard."""
    event_id: str
    event_name: str
    metric_type: str = Field(..., pattern="^(GAUGE|COUNTER|HISTOGRAM|ALERT)$")
    value: float
    trace_id: str
    tags: Dict[str, str] = Field(default_factory=dict)
    emitted_at: str


# -----------------------------------------------------------------------------
# 6. BHIV Common Core: Primary Operations & Parikshak Review Contracts
# -----------------------------------------------------------------------------
class CoreOperationalRequest(StrictBaseModel):
    """Main inbound payload for BHIV Enterprise Core execution."""
    request_id: str = Field(..., min_length=4, max_length=128)
    task_id: str = Field(..., min_length=3, max_length=64)
    actor_id: str = Field(..., min_length=2, max_length=128)
    role: str = Field(..., min_length=2, max_length=64)
    intent: str = Field(..., min_length=2, max_length=64)
    payload: Dict[str, Any] = Field(default_factory=dict)
    trace_id: Optional[str] = None


class CoreOperationalResponse(StrictBaseModel):
    """Main outbound response from BHIV Enterprise Core."""
    status: str
    request_id: str
    task_id: str
    state: WorkflowStateEnum
    trace_id: str
    result: Dict[str, Any] = Field(default_factory=dict)
    evidence_receipt: Optional[AuditStorageReceipt] = None
    ledger_entry: Optional[GovernanceLedgerEntry] = None
    error: Optional[str] = None
    schema_version: str = SCHEMA_VERSION


class DeterministicStateHashRecord(StrictBaseModel):
    """Verifiable proof record for 50-consecutive-run stability."""
    run_index: int = Field(..., ge=1, le=100)
    input_digest: str
    normalized_state_hash: str = Field(..., min_length=64, max_length=64)
    volatile_keys_stripped: List[str]
    is_identical_to_baseline: bool
    execution_time_ms: float


class ReviewEvaluationVerdict(StrictBaseModel):
    """Parikshak review verdict record."""
    evaluation_id: str
    task_id: str
    candidate_id: str
    score: float = Field(..., ge=0.0, le=100.0)
    verdict: str = Field("PASS", pattern="^(PASS|FAIL|REVISION_REQUIRED)$")
    maturity: str
    learning_velocity: float
    weakness_focus: str
    passed_quality_gates: List[str]
    timestamp: str
    schema_version: str = SCHEMA_VERSION


class OperationalReviewPacket(StrictBaseModel):
    """Comprehensive governed review packet adhering to SETU OS Architecture v6.0."""
    task_id: str
    candidate_name: str
    verdict: ReviewEvaluationVerdict
    architectural_standards_checked: List[str]
    deterministic_runs_verified: int = 50
    state_hash_sha256: str
    zero_500_exceptions_confirmed: bool = True
    five_tier_test_pass_rate_percent: float = 100.0
    evidence_index: Dict[str, str]
    schema_version: str = SCHEMA_VERSION
