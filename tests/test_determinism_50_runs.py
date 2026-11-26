"""
tests/test_determinism_50_runs.py
=================================
Tier 3: 50-Run Deterministic State Hash Verification.
Executes 50 consecutive independent runs of identical workflow parameters.
Asserts that all 50 runs produce 100% identical SHA-256 state hashes.
"""

import json
from pathlib import Path
from contracts.schemas import CoreOperationalRequest
from src.enterprise_core.core_engine import EnterpriseCoreEngine
from src.enterprise_core.determinism import compute_sha256


class TestFiftyRunDeterminism:
    """Verifies that 50 consecutive workflow runs yield identical SHA-256 state hashes."""

    def test_fifty_consecutive_runs_produce_identical_hash(self, tmp_path):
        benchmark_payload = {
            "campaign_name": "BHIV Core Verification Mission",
            "budget": 15000.0,
            "channel": "linkedin",
            "objective": "Zero-defect enterprise execution",
        }

        generated_hashes = []
        hash_records = []

        baseline_hash = None

        for run_idx in range(1, 51):
            run_tmp = tmp_path / f"run_{run_idx}"
            engine = EnterpriseCoreEngine(bucket_dir=str(run_tmp))
            req_id = "REQ-BENCHMARK-DETERMINISM-FIXED"

            # 1. Intake
            engine.process_intake(
                CoreOperationalRequest(
                    request_id=req_id,
                    task_id="T-OUT-OF-SYLLABUS",
                    actor_id="pratik.bhuwad",
                    role="Product Owner",
                    intent="DETERMINISTIC_BENCHMARK",
                    payload=benchmark_payload,
                )
            )

            # 2. Policy Evaluation
            engine.evaluate_policy_compliance(req_id)

            # 3. Governed Approval
            engine.execute_governed_approval(
                request_id=req_id,
                reviewer_name="Pratik Bhuwad - Product Owner",
                decision_notes="Canonical verification approval.",
            )

            # 4. Dispatch to Niyantran
            dispatch_res = engine.dispatch_to_niyantran(
                request_id=req_id,
                target_agent="Pratik Bhuwad",
                title="Execute Canonical Specification",
                calibrated_duration_mins=180,
            )

            # Extract normalized state hash of the terminal state
            fsm = engine.active_workflows[req_id]
            state_hash = fsm.compute_current_state_hash()

            if baseline_hash is None:
                baseline_hash = state_hash

            is_identical = (state_hash == baseline_hash)
            generated_hashes.append(state_hash)
            hash_records.append({
                "run_index": run_idx,
                "state_hash": state_hash,
                "is_identical_to_baseline": is_identical,
            })

            assert is_identical, f"Determinism drift at run {run_idx}: {state_hash} != {baseline_hash}"

        # Assert all 50 hashes are identical
        assert len(generated_hashes) == 50
        assert len(set(generated_hashes)) == 1, f"State hash was not stable: {set(generated_hashes)}"

        # Save verifiable evidence to review_packets/Evidence/
        evidence_dir = Path("review_packets/Evidence")
        evidence_dir.mkdir(parents=True, exist_ok=True)
        evidence_file = evidence_dir / "deterministic_state_hashes_50_runs.json"

        with open(evidence_file, "w", encoding="utf-8") as f:
            json.dump({
                "task_id": "T-OUT-OF-SYLLABUS",
                "iterations_verified": 50,
                "deterministic_sha256": baseline_hash,
                "stability_rate_percent": 100.0,
                "verdict": "VERIFIED_IDENTICAL",
                "runs": hash_records,
            }, f, indent=2)

        assert evidence_file.exists()
