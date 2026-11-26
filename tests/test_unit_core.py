"""
tests/test_unit_core.py
=======================
Tier 1: Unit Tests for BHIV Enterprise Core.
Tests schema constraints, deterministic normalizer, and state machine transition invariants.
"""

import pytest
from pydantic import ValidationError
from contracts.schemas import (
    TaskAssignmentRequest,
    PolicyEvaluationRequest,
    AuditEvidenceEnvelope,
    WorkflowStateEnum,
    CoreOperationalRequest,
)
from src.enterprise_core.determinism import (
    normalize_for_determinism,
    canonical_json,
    compute_sha256,
)
from src.enterprise_core.state_machine import (
    EnterpriseStateMachine,
    StateTransitionError,
)


class TestSchemaConstraints:
    """Verifies strict Schema v1.0 enforcement and extra field prohibition."""

    def test_schema_extra_fields_forbidden(self):
        """Inbound payloads with arbitrary unexpected fields must fail validation."""
        valid_data = {
            "policy_id": "POL-MKT-001",
            "actor_id": "actor-pratik",
            "actor_role": "Product Owner",
            "parameters": {"budget": 25000.0},
            "context_tags": ["tag1"],
        }
        # Valid data passes
        req = PolicyEvaluationRequest(**valid_data)
        assert req.policy_id == "POL-MKT-001"

        # Extra injected field fails
        with pytest.raises(ValidationError):
            PolicyEvaluationRequest(**{**valid_data, "unauthorized_injected_key": "malicious_payload"})

    def test_task_assignment_request_validation(self):
        """Task assignment requires valid format and non-empty parameters."""
        req = TaskAssignmentRequest(
            task_id="T-OUT-OF-SYLLABUS",
            target_agent="Pratik Bhuwad",
            title="Enterprise Core Logic & Verification",
            priority="HIGH",
            calibrated_duration_mins=180,
            spec_payload={"objective": "Enterprise core stabilization"},
            assigned_by="Parikshak Reviewer",
        )
        assert req.priority == "HIGH"
        assert req.calibrated_duration_mins == 180

        # Duration < 15 must fail
        with pytest.raises(ValidationError):
            TaskAssignmentRequest(
                task_id="T-OUT-OF-SYLLABUS",
                target_agent="Pratik",
                title="Short Task",
                priority="HIGH",
                calibrated_duration_mins=5,
                spec_payload={},
                assigned_by="Reviewer",
            )


class TestDeterminismUtility:
    """Verifies volatile field stripping and canonical serialization."""

    def test_volatile_fields_stripped(self):
        data = {
            "task_id": "T-100",
            "timestamp": "2026-11-26T12:00:00Z",
            "trace_id": "TRC-9999",
            "pid": 1234,
            "status": "APPROVED",
            "details": {
                "execution_time_ms": 45.2,
                "score": 100.0,
            },
        }
        normalized = normalize_for_determinism(data)
        assert "timestamp" not in normalized
        assert "trace_id" not in normalized
        assert "pid" not in normalized
        assert "execution_time_ms" not in normalized["details"]
        assert normalized["task_id"] == "T-100"
        assert normalized["status"] == "APPROVED"
        assert normalized["details"]["score"] == 100.0

    def test_canonical_json_key_sorting(self):
        d1 = {"z": 1, "a": 2, "m": 3}
        d2 = {"a": 2, "m": 3, "z": 1}
        assert canonical_json(d1) == canonical_json(d2)
        assert compute_sha256(d1) == compute_sha256(d2)


class TestStateMachineInvariants:
    """Verifies state machine determinism, boundary defense, and prohibited mutations."""

    def test_valid_progression(self):
        fsm = EnterpriseStateMachine("T-01", "REQ-01", "ACTOR-01", {"budget": 10000.0})
        assert fsm.state == WorkflowStateEnum.INTAKE

        fsm.transition_to(WorkflowStateEnum.POLICY_VALIDATION, "Validating policy")
        assert fsm.state == WorkflowStateEnum.POLICY_VALIDATION

        fsm.transition_to(WorkflowStateEnum.EVALUATION_PENDING, "Evaluation done")
        assert fsm.state == WorkflowStateEnum.EVALUATION_PENDING

        fsm.transition_to(WorkflowStateEnum.AWAITING_REVIEW, "Awaiting review")
        assert fsm.state == WorkflowStateEnum.AWAITING_REVIEW

        fsm.transition_to(
            WorkflowStateEnum.GOVERNED_APPROVAL,
            reason="Approved with verified citations",
            actor="Pratik Bhuwad - Product Owner",
        )
        assert fsm.state == WorkflowStateEnum.GOVERNED_APPROVAL
        assert fsm.reviewer_identity == "Pratik Bhuwad - Product Owner"

        fsm.transition_to(
            WorkflowStateEnum.NIYANTRAN_DISPATCH,
            reason="Dispatching to Niyantran",
            actor="Parikshak",
        )
        assert fsm.state == WorkflowStateEnum.NIYANTRAN_DISPATCH

        fsm.transition_to(WorkflowStateEnum.COMMITTED, "Committed", actor="System")
        assert fsm.state == WorkflowStateEnum.COMMITTED
        assert fsm.is_terminal is True

    def test_prohibited_state_jump(self):
        """Attempting to jump from INTAKE directly to COMMITTED must raise StateTransitionError."""
        fsm = EnterpriseStateMachine("T-02", "REQ-02", "ACTOR-02", {})
        with pytest.raises(StateTransitionError) as exc_info:
            fsm.transition_to(WorkflowStateEnum.COMMITTED, "Unauthorized skip")
        assert "Forbidden transition" in str(exc_info.value)

    def test_terminal_state_mutation_prohibited(self):
        """No transitions permitted once a workflow is COMMITTED."""
        fsm = EnterpriseStateMachine("T-03", "REQ-03", "ACTOR-03", {})
        fsm.state = WorkflowStateEnum.COMMITTED
        fsm.is_terminal = True

        with pytest.raises(StateTransitionError) as exc_info:
            fsm.transition_to(WorkflowStateEnum.INTAKE, "Unauthorized reset")
        assert "terminal state" in str(exc_info.value)

    def test_invalid_reviewer_identity_rejected(self):
        """Approval by blank or default evaluators must be strictly rejected."""
        fsm = EnterpriseStateMachine("T-04", "REQ-04", "ACTOR-04", {})
        fsm.transition_to(WorkflowStateEnum.POLICY_VALIDATION, "pol")
        fsm.transition_to(WorkflowStateEnum.EVALUATION_PENDING, "eval")
        fsm.transition_to(WorkflowStateEnum.AWAITING_REVIEW, "wait")

        # Blank reviewer fails
        with pytest.raises(StateTransitionError) as exc1:
            fsm.transition_to(WorkflowStateEnum.GOVERNED_APPROVAL, "ok", actor="")
        assert "Reviewer identity integrity violation" in str(exc1.value)

        # Default evaluator fails
        with pytest.raises(StateTransitionError) as exc2:
            fsm.transition_to(WorkflowStateEnum.GOVERNED_APPROVAL, "ok", actor="Prof_Evaluator")
        assert "Reviewer identity integrity violation" in str(exc2.value)
