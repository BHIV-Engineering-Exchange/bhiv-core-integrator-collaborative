"""
src/enterprise_core/integrations/shakti_adapter.py
==================================================
GC Shakti: Governance Intelligence & Policy Authority Adapter.
Enforces organizational policy compliance, spending caps, and rule evaluation.
"""

from __future__ import annotations

from typing import Any, Dict, List
from contracts.schemas import (
    PolicyEvaluationRequest,
    PolicyEvaluationResult,
    PolicyStatusEnum,
)


class GCShaktiAdapter:
    """Client adapter for GC Shakti Policy Intelligence."""

    def __init__(self):
        # Known policy rules catalog
        self.channel_caps: Dict[str, float] = {
            "linkedin": 15000.0,
            "google_search": 25000.0,
            "meta_instagram": 20000.0,
            "linear_tv": 0.0,  # Prohibited / Insufficient evidence
        }
        self.max_proposal_budget: float = 50000.0

    def evaluate_policy(self, request: PolicyEvaluationRequest) -> PolicyEvaluationResult:
        """Evaluates inbound proposal parameters against GC Shakti policy standards."""
        violations: List[str] = []
        citations: List[str] = []
        status = PolicyStatusEnum.PASS
        condition_notes: str | None = None
        compliance_score = 100.0

        params = request.parameters
        budget = float(params.get("budget", 0.0))
        channel = str(params.get("channel", "")).lower()

        # Check total budget cap
        if budget > self.max_proposal_budget:
            violations.append(
                f"Requested budget ${budget:,.2f} exceeds total organizational cap of ${self.max_proposal_budget:,.2f}"
            )
            citations.append("DOC-MKT-002:Sec-1-Budget-Cap")
            compliance_score -= 50.0

        # Check channel cap variance
        if channel in self.channel_caps:
            cap = self.channel_caps[channel]
            if cap == 0.0:
                # Prohibited channel
                status = PolicyStatusEnum.INSUFFICIENT_EVIDENCE
                violations.append(f"Channel '{channel}' is prohibited or lacks verified performance benchmarks.")
                citations.append("DOC-MKT-004:Sec-3-Channel-Prohibitions")
                return PolicyEvaluationResult(
                    policy_id=request.policy_id,
                    status=status,
                    compliance_score=0.0,
                    violations=violations,
                    citations=citations,
                    condition_notes="Abstain: Insufficient verified evidence for channel.",
                )
            elif budget > cap:
                variance = budget - cap
                violations.append(
                    f"Requested spend of ${budget:,.2f} for '{channel}' exceeds specific channel cap of ${cap:,.2f} by ${variance:,.2f}."
                )
                citations.append("DOC-MKT-002:Sec-2-Channel-Caps")
                status = PolicyStatusEnum.CONDITIONAL
                condition_notes = f"Approval conditional upon managerial exception sign-off for channel variance of ${variance:,.2f}."
                compliance_score = max(0.0, compliance_score - 25.0)
        elif channel:
            # Unknown channel
            citations.append("DOC-MKT-004:Sec-Unknown-Channel")

        if violations and status == PolicyStatusEnum.PASS:
            status = PolicyStatusEnum.FAIL

        return PolicyEvaluationResult(
            policy_id=request.policy_id,
            status=status,
            compliance_score=compliance_score,
            violations=violations,
            citations=citations,
            condition_notes=condition_notes,
        )
