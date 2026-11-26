"""
tests/test_negative_error_boundaries.py
=======================================
Tier 4: Negative & Error Boundary Tests.
Verifies zero unhandled 500 exceptions, canonical refusal on malformed inputs, and security gates.
"""

import pytest
from pydantic import ValidationError
from contracts.schemas import CoreOperationalRequest, WorkflowStateEnum
from src.enterprise_core.api import (
    submit_review_intake,
    evaluate_compliance,
    approve_review,
    dispatch_assignment,
    get_governance_audit,
    health_check,
    system_status,
    ApprovalRequestPayload,
    DispatchRequestPayload,
)
from src.enterprise_core.core_engine import EnterpriseCoreEngine
from src.enterprise_core.error_boundary import (
    EnterpriseErrorBoundary,
    sanitize_error_response,
)
from src.enterprise_core.state_machine import StateTransitionError


class TestNegativeAndErrorBoundaries:
    """Verifies that all error scenarios return sanitized error contracts with zero 500 crashes."""

    @pytest.fixture
    def engine(self, tmp_path):
        return EnterpriseCoreEngine(bucket_dir=str(tmp_path))

    def test_malformed_payload_sanitized_to_422_contract(self):
        """Invalid schema input must be sanitized into a structured 422 error contract."""
        with pytest.raises(ValidationError) as exc_info:
            CoreOperationalRequest(**{"invalid": "payload"})

        sanitized = sanitize_error_response(exc_info.value, trace_id="TRC-TEST-422")
        assert sanitized["status"] == "ERROR"
        assert sanitized["error_code"] == "SCHEMA_VALIDATION_ERROR"
        assert sanitized["status_code"] == 422
        assert "trace_id" in sanitized
        assert "Inbound payload failed Schema v1.0 validation" in sanitized["message"]

    def test_missing_workflow_audit_sanitized_to_404(self):
        """Referencing non-existent workflow returns sanitized 404 contract."""
        with pytest.raises(KeyError) as exc_info:
            get_governance_audit("NON-EXISTENT-ID-999")

        sanitized = sanitize_error_response(exc_info.value, trace_id="TRC-TEST-404")
        assert sanitized["status"] == "ERROR"
        assert sanitized["error_code"] == "MISSING_REQUIRED_RESOURCE"
        assert sanitized["status_code"] == 404

    def test_duplicate_approval_rejection(self, engine):
        """Attempting to approve a finalized/terminal workflow raises StateTransitionError."""
        req_id = "REQ-DUPLICATE-001"
        engine.process_intake(
            CoreOperationalRequest(
                request_id=req_id,
                task_id="T-OUT-OF-SYLLABUS",
                actor_id="pratik",
                role="Product Owner",
                intent="TEST",
                payload={"budget": 10000.0, "channel": "linkedin"},
            )
        )
        engine.evaluate_policy_compliance(req_id)
        # First approval succeeds
        engine.execute_governed_approval(req_id, "Pratik Bhuwad", "Initial approval.")
        # Dispatch commits to terminal state
        engine.dispatch_to_niyantran(req_id, "Pratik", "Task Title")

        # Second approval on terminal state must fail
        with pytest.raises(StateTransitionError) as exc_info:
            engine.execute_governed_approval(req_id, "Pratik Bhuwad", "Duplicate approval attempt.")
        assert "terminal state" in str(exc_info.value)

        # Sanitize error
        sanitized = sanitize_error_response(exc_info.value)
        assert sanitized["status"] == "ERROR"
        assert sanitized["error_code"] == "STATE_TRANSITION_VIOLATION"
        assert sanitized["status_code"] == 400

    def test_prohibited_channel_abstention(self, engine):
        """Proposals for prohibited channels (e.g. Linear TV) must abstain with INSUFFICIENT_EVIDENCE."""
        req_id = "REQ-TV-PROHIBITED"
        engine.process_intake(
            CoreOperationalRequest(
                request_id=req_id,
                task_id="T-OUT-OF-SYLLABUS",
                actor_id="pratik",
                role="Product Owner",
                intent="TEST",
                payload={"budget": 10000.0, "channel": "linear_tv"},
            )
        )
        res = engine.evaluate_policy_compliance(req_id)
        compliance = res.result["compliance"]
        assert compliance["status"] == "INSUFFICIENT_EVIDENCE"
        assert compliance["compliance_score"] == 0.0

    def test_error_boundary_catches_arbitrary_exception(self):
        """Universal Error Boundary safely intercepts any uncaught exception without crashing."""
        boundary = EnterpriseErrorBoundary(trace_id="TRC-SAFE-01")

        def faulty_function():
            raise RuntimeError("Database connection suddenly dropped")

        result = boundary.execute_safely(faulty_function)
        assert result["status"] == "ERROR"
        assert result["error_code"] == "OPERATIONAL_EXECUTION_ERROR"
        assert result["status_code"] == 400
        assert "Database connection suddenly dropped" not in result["message"] or "RuntimeError" in result["message"]

    def test_api_route_functions_execution(self):
        """Directly verifies FastAPI route functions execute cleanly."""
        h = health_check()
        assert h["status"] == "HEALTHY"
        assert h["schema_version"] == "1.0.0"

        s = system_status()
        assert s["status"] == "OPERATIONAL"
        assert s["ledger_integrity"] is True
