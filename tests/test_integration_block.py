"""
tests/test_integration_block.py
================================
Tier 2: Integration Tests across the 6-Pillar Ecosystem Block.
Verifies BHIV Core, GC Shakti, Niyantran, Bucket, Gov-OS, and Saarthi interoperation.
"""

import pytest
from contracts.schemas import (
    CoreOperationalRequest,
    WorkflowStateEnum,
    PolicyStatusEnum,
)
from src.enterprise_core.core_engine import EnterpriseCoreEngine


class TestIntegrationBlock:
    """Verifies end-to-end integration across all 6 architectural pillars."""

    @pytest.fixture
    def engine(self, tmp_path):
        bucket_dir = tmp_path / "bucket_test_records"
        return EnterpriseCoreEngine(bucket_dir=str(bucket_dir))

    def test_full_governed_lifecycle_e2e(self, engine):
        req_id = "REQ-INTEG-E2E-001"
        task_id = "T-OUT-OF-SYLLABUS"

        # 1. Intake
        intake_req = CoreOperationalRequest(
            request_id=req_id,
            task_id=task_id,
            actor_id="pratik.bhuwad",
            role="Product Owner",
            intent="ENTERPRISE_CORE_VERIFICATION",
            payload={
                "campaign_name": "Q4 Enterprise System Transition",
                "budget": 20000.0,
                "channel": "linkedin",
            },
        )
        intake_res = engine.process_intake(intake_req)
        assert intake_res.status == "SUCCESS"
        assert intake_res.state == WorkflowStateEnum.INTAKE
        assert intake_res.evidence_receipt is not None
        assert intake_res.evidence_receipt.status == "STORED"

        # 2. GC Shakti Policy Evaluation
        eval_res = engine.evaluate_policy_compliance(req_id)
        assert eval_res.status == "SUCCESS"
        assert eval_res.state == WorkflowStateEnum.AWAITING_REVIEW
        compliance = eval_res.result["compliance"]
        # $20,000 for linkedin exceeds $15,000 cap -> CONDITIONAL
        assert compliance["status"] == PolicyStatusEnum.CONDITIONAL.value
        assert "DOC-MKT-002:Sec-2-Channel-Caps" in compliance["citations"]

        # 3. Governed Approval (Explicit Human Reviewer)
        approval_res = engine.execute_governed_approval(
            request_id=req_id,
            reviewer_name="Pratik Bhuwad - Product Owner",
            decision_notes="Approved with managerial exception for LinkedIn Q4 scale-up.",
        )
        assert approval_res.status == "SUCCESS"
        assert approval_res.state == WorkflowStateEnum.GOVERNED_APPROVAL
        assert approval_res.ledger_entry is not None
        assert approval_res.ledger_entry.status == "COMMITTED"
        assert approval_res.ledger_entry.block_index == 1

        # 4. Niyantran Auto-Assignment & Dispatch
        dispatch_res = engine.dispatch_to_niyantran(
            request_id=req_id,
            target_agent="Pratik Bhuwad",
            title="Execute SETU OS Architecture v6.0 Verification",
            calibrated_duration_mins=180,
        )
        assert dispatch_res.status == "SUCCESS"
        assert dispatch_res.state == WorkflowStateEnum.COMMITTED
        assert dispatch_res.result["is_committed"] is True
        assignment = dispatch_res.result["assignment"]
        assert assignment["target_agent"] == "Pratik Bhuwad"
        assert assignment["status"] == "ASSIGNED"

        # 5. Gov-OS Ledger Verification
        assert engine.gov_os.verify_ledger_integrity() is True
        attestation = engine.gov_os.verify_state_attestation(dispatch_res.result["final_state_hash"])
        assert attestation.is_valid is True

        # 6. Saarthi Telemetry Verification
        metrics = engine.saarthi.get_latest_metrics()
        assert len(metrics) >= 2
        event_names = [m["event_name"] for m in metrics]
        assert "workflow_intake_initialized" in event_names
        assert "policy_evaluated" in event_names
