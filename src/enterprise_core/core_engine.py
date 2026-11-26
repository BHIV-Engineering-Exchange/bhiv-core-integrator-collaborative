"""
src/enterprise_core/core_engine.py
==================================
BHIV Enterprise Core Engine (SETU OS Architecture v6.0).
Coordinates the complete lifecycle across the 6-pillar ecosystem.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, Optional

from contracts.schemas import (
    CoreOperationalRequest,
    CoreOperationalResponse,
    WorkflowStateEnum,
    PolicyEvaluationRequest,
    PolicyEvaluationResult,
    AuditEvidenceEnvelope,
    AuditStorageReceipt,
    TaskAssignmentRequest,
    TaskAssignmentResponse,
    GovernanceLedgerEntry,
    SCHEMA_VERSION,
)

from .state_machine import EnterpriseStateMachine, StateTransitionError
from .determinism import compute_sha256
from .integrations.shakti_adapter import GCShaktiAdapter
from .integrations.niyantran_adapter import NiyantranAdapter
from .integrations.bucket_adapter import BucketAuditAdapter
from .integrations.gov_os_adapter import GovOSLedgerAdapter
from .integrations.saarthi_adapter import SaarthiTelemetryAdapter


class EnterpriseCoreEngine:
    """
    Primary orchestration engine for BHIV Enterprise Operating System Common Core.
    Guarantees deterministic execution, error boundary enforcement, and multi-pillar sync.
    """

    def __init__(self, bucket_dir: str = "data/bucket_records"):
        self.shakti = GCShaktiAdapter()
        self.niyantran = NiyantranAdapter()
        self.bucket = BucketAuditAdapter(storage_dir=bucket_dir)
        self.gov_os = GovOSLedgerAdapter()
        self.saarthi = SaarthiTelemetryAdapter()
        self.active_workflows: Dict[str, EnterpriseStateMachine] = {}

    def process_intake(self, request: CoreOperationalRequest) -> CoreOperationalResponse:
        """Initializes a new governed workflow under SETU OS Architecture v6.0."""
        trace_id = request.trace_id or f"TRC-{datetime.datetime.now().strftime('%Y%m%d')}-{compute_sha256(request.request_id)[:8].upper()}"

        # Initialize FSM
        fsm = EnterpriseStateMachine(
            task_id=request.task_id,
            request_id=request.request_id,
            actor_id=request.actor_id,
            initial_payload=request.payload,
        )
        self.active_workflows[request.request_id] = fsm

        # Record telemetry in Saarthi
        self.saarthi.emit_metric(
            event_name="workflow_intake_initialized",
            metric_type="COUNTER",
            value=1.0,
            trace_id=trace_id,
            tags={"task_id": request.task_id, "state": fsm.state.value},
        )

        # Store intake envelope into Bucket
        receipt = self.bucket.store_evidence(
            AuditEvidenceEnvelope(
                artifact_id=f"INTAKE-{request.request_id}",
                artifact_type="instruction",
                trace_id=trace_id,
                timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                data=fsm.get_state_snapshot(),
                metadata={"request_id": request.request_id, "schema_version": SCHEMA_VERSION},
            )
        )

        return CoreOperationalResponse(
            status="SUCCESS",
            request_id=request.request_id,
            task_id=request.task_id,
            state=fsm.state,
            trace_id=trace_id,
            result={"message": "Intake successfully registered and state initialized in INTAKE mode."},
            evidence_receipt=receipt,
            schema_version=SCHEMA_VERSION,
        )

    def evaluate_policy_compliance(self, request_id: str, policy_id: str = "POL-ENTERPRISE-001") -> CoreOperationalResponse:
        """Validates current workflow parameters against GC Shakti policy rules."""
        if request_id not in self.active_workflows:
            raise KeyError(f"Workflow request '{request_id}' not found.")

        fsm = self.active_workflows[request_id]
        trace_id = f"TRC-EVAL-{request_id}"

        # Transition to POLICY_VALIDATION
        fsm.transition_to(
            WorkflowStateEnum.POLICY_VALIDATION,
            reason="Initiating GC Shakti policy compliance inspection.",
        )

        # Execute GC Shakti evaluation
        shakti_req = PolicyEvaluationRequest(
            policy_id=policy_id,
            actor_id=fsm.actor_id,
            actor_role="Product Owner",
            parameters=fsm.payload,
            context_tags=["enterprise_core", "compliance"],
        )
        shakti_result = self.shakti.evaluate_policy(shakti_req)

        # Progress to EVALUATION_PENDING and AWAITING_REVIEW
        fsm.transition_to(
            WorkflowStateEnum.EVALUATION_PENDING,
            reason="GC Shakti policy evaluation completed.",
            data_update={"compliance_evaluation": shakti_result.model_dump()},
        )

        fsm.transition_to(
            WorkflowStateEnum.AWAITING_REVIEW,
            reason="Holding for explicit human managerial review.",
        )

        self.saarthi.emit_metric(
            event_name="policy_evaluated",
            metric_type="GAUGE",
            value=shakti_result.compliance_score,
            trace_id=trace_id,
            tags={"compliance_status": shakti_result.status.value},
        )

        receipt = self.bucket.store_evidence(
            AuditEvidenceEnvelope(
                artifact_id=f"EVAL-{request_id}",
                artifact_type="contract",
                trace_id=trace_id,
                timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                data=fsm.get_state_snapshot(),
                metadata={"compliance_status": shakti_result.status.value},
            )
        )

        return CoreOperationalResponse(
            status="SUCCESS",
            request_id=request_id,
            task_id=fsm.task_id,
            state=fsm.state,
            trace_id=trace_id,
            result={
                "compliance": shakti_result.model_dump(),
                "governance_status": "AWAITING_HUMAN_APPROVAL",
            },
            evidence_receipt=receipt,
            schema_version=SCHEMA_VERSION,
        )

    def execute_governed_approval(
        self,
        request_id: str,
        reviewer_name: str,
        decision_notes: str,
    ) -> CoreOperationalResponse:
        """Applies governed approval by an explicit authorized human reviewer."""
        if request_id not in self.active_workflows:
            raise KeyError(f"Workflow request '{request_id}' not found.")

        fsm = self.active_workflows[request_id]
        trace_id = f"TRC-APP-{request_id}"

        # Transition to GOVERNED_APPROVAL
        fsm.transition_to(
            WorkflowStateEnum.GOVERNED_APPROVAL,
            reason=decision_notes,
            actor=reviewer_name,
            data_update={"approval_decision": {"reviewer": reviewer_name, "notes": decision_notes}},
        )

        # Record in Gov-OS
        ledger_entry = self.gov_os.commit_state_transition(
            task_id=fsm.task_id,
            transaction_id=f"TX-{request_id}-APP",
            trace_id=trace_id,
            state_snapshot=fsm.get_state_snapshot(),
        )

        # Store in Bucket
        receipt = self.bucket.store_evidence(
            AuditEvidenceEnvelope(
                artifact_id=f"APPROVAL-{request_id}",
                artifact_type="authority",
                trace_id=trace_id,
                timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                data=fsm.get_state_snapshot(),
                metadata={"reviewer": reviewer_name, "block_index": ledger_entry.block_index},
            )
        )

        return CoreOperationalResponse(
            status="SUCCESS",
            request_id=request_id,
            task_id=fsm.task_id,
            state=fsm.state,
            trace_id=trace_id,
            result={
                "message": f"Proposal approved by {reviewer_name}.",
                "state_hash": ledger_entry.state_hash,
                "block_index": ledger_entry.block_index,
            },
            evidence_receipt=receipt,
            ledger_entry=ledger_entry,
            schema_version=SCHEMA_VERSION,
        )

    def dispatch_to_niyantran(
        self,
        request_id: str,
        target_agent: str,
        title: str,
        calibrated_duration_mins: int = 180,
    ) -> CoreOperationalResponse:
        """Dispatches approved workflow into Niyantran engine for auto-assignment."""
        if request_id not in self.active_workflows:
            raise KeyError(f"Workflow request '{request_id}' not found.")

        fsm = self.active_workflows[request_id]
        trace_id = f"TRC-DISP-{request_id}"

        # Transition to NIYANTRAN_DISPATCH
        fsm.transition_to(
            WorkflowStateEnum.NIYANTRAN_DISPATCH,
            reason=f"Dispatching task '{fsm.task_id}' to agent '{target_agent}'.",
            actor=fsm.reviewer_identity or "GOVERNANCE_SYSTEM",
        )

        # Dispatch via Niyantran adapter
        assignment = self.niyantran.dispatch_assignment(
            TaskAssignmentRequest(
                task_id=fsm.task_id,
                target_agent=target_agent,
                title=title,
                priority="HIGH",
                calibrated_duration_mins=calibrated_duration_mins,
                spec_payload={
                    "request_id": request_id,
                    "target_product": "BHIV Enterprise Operating System Common Core",
                    "execution_standard": "SETU OS Architecture v6.0",
                    "approved_parameters": fsm.payload,
                    "governance_approval": fsm.approval_notes,
                },
                assigned_by=fsm.reviewer_identity or "Parikshak",
            ),
            trace_id=trace_id,
        )

        # Transition to COMMITTED (terminal)
        fsm.transition_to(
            WorkflowStateEnum.COMMITTED,
            reason="Task successfully assigned and committed to ecosystem execution.",
            actor="NIYANTRAN_LIFECYCLE",
            data_update={"assignment": assignment.model_dump()},
        )

        ledger_entry = self.gov_os.commit_state_transition(
            task_id=fsm.task_id,
            transaction_id=f"TX-{request_id}-COMMITTED",
            trace_id=trace_id,
            state_snapshot=fsm.get_state_snapshot(),
        )

        receipt = self.bucket.store_evidence(
            AuditEvidenceEnvelope(
                artifact_id=f"DISPATCH-{request_id}",
                artifact_type="execution",
                trace_id=trace_id,
                timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                data=fsm.get_state_snapshot(),
                metadata={"assignment_id": assignment.assignment_id},
            )
        )

        return CoreOperationalResponse(
            status="SUCCESS",
            request_id=request_id,
            task_id=fsm.task_id,
            state=fsm.state,
            trace_id=trace_id,
            result={
                "assignment": assignment.model_dump(),
                "final_state_hash": ledger_entry.state_hash,
                "is_committed": True,
            },
            evidence_receipt=receipt,
            ledger_entry=ledger_entry,
            schema_version=SCHEMA_VERSION,
        )
