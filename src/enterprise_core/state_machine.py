"""
src/enterprise_core/state_machine.py
====================================
Deterministic Finite State Machine for BHIV Enterprise Core.
Enforces strict transitions and prohibits unauthorized direct mutations.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional
from contracts.schemas import WorkflowStateEnum
from .determinism import compute_sha256, normalize_for_determinism


class StateTransitionError(Exception):
    """Raised when an invalid or unauthorized state transition is attempted."""
    pass


FORBIDDEN_REVIEWERS = {
    "prof_evaluator",
    "anonymous",
    "unknown",
    "default_reviewer",
    "evaluator",
    "",
}

# Strict valid progression transitions
VALID_TRANSITIONS: Dict[WorkflowStateEnum, List[WorkflowStateEnum]] = {
    WorkflowStateEnum.INTAKE: [WorkflowStateEnum.POLICY_VALIDATION, WorkflowStateEnum.REJECTED],
    WorkflowStateEnum.POLICY_VALIDATION: [WorkflowStateEnum.EVALUATION_PENDING, WorkflowStateEnum.REJECTED],
    WorkflowStateEnum.EVALUATION_PENDING: [WorkflowStateEnum.AWAITING_REVIEW, WorkflowStateEnum.REJECTED],
    WorkflowStateEnum.AWAITING_REVIEW: [WorkflowStateEnum.GOVERNED_APPROVAL, WorkflowStateEnum.REJECTED],
    WorkflowStateEnum.GOVERNED_APPROVAL: [WorkflowStateEnum.NIYANTRAN_DISPATCH, WorkflowStateEnum.REJECTED],
    WorkflowStateEnum.NIYANTRAN_DISPATCH: [WorkflowStateEnum.COMMITTED, WorkflowStateEnum.REJECTED],
    WorkflowStateEnum.COMMITTED: [],  # Terminal immutable state
    WorkflowStateEnum.REJECTED: [],   # Terminal immutable state
}


class EnterpriseStateMachine:
    """
    Deterministic state machine for mission-critical engineering reviews and workflows.
    Guarantees state immutability, audit logging, and cryptographic hashing.
    """

    def __init__(self, task_id: str, request_id: str, actor_id: str, initial_payload: Dict[str, Any]):
        self.task_id = task_id
        self.request_id = request_id
        self.actor_id = actor_id
        self.state: WorkflowStateEnum = WorkflowStateEnum.INTAKE
        self.payload: Dict[str, Any] = copy.deepcopy(initial_payload)
        self.history: List[Dict[str, Any]] = []
        self.reviewer_identity: Optional[str] = None
        self.approval_notes: Optional[str] = None
        self.is_terminal: bool = False

        # Record initial intake event
        self._record_event(WorkflowStateEnum.INTAKE, "Workflow intake registered and state initialized.")

    def _record_event(self, state: WorkflowStateEnum, reason: str, actor: Optional[str] = None) -> None:
        event = {
            "state": state.value,
            "reason": reason,
            "actor": actor or self.actor_id,
            "state_digest": compute_sha256(self.payload),
        }
        self.history.append(event)

    def transition_to(self, new_state: WorkflowStateEnum, reason: str, actor: Optional[str] = None, data_update: Optional[Dict[str, Any]] = None) -> WorkflowStateEnum:
        """
        Executes a validated transition to a new state.
        Prohibits state jumps, terminal state mutations, and invalid reviewers.
        """
        if self.is_terminal:
            raise StateTransitionError(
                f"Unauthorized direct mutation: Workflow '{self.task_id}' is in terminal state '{self.state.value}'. No further transitions permitted."
            )

        valid_next_states = VALID_TRANSITIONS.get(self.state, [])
        if new_state not in valid_next_states:
            raise StateTransitionError(
                f"Forbidden transition: Cannot transition from '{self.state.value}' to '{new_state.value}'. "
                f"Permitted transitions: {[s.value for s in valid_next_states]}"
            )

        # Reviewer integrity check for GOVERNED_APPROVAL
        if new_state == WorkflowStateEnum.GOVERNED_APPROVAL:
            acting_reviewer = (actor or "").strip()
            if not acting_reviewer or acting_reviewer.lower() in FORBIDDEN_REVIEWERS:
                raise StateTransitionError(
                    f"Reviewer identity integrity violation: Invalid reviewer '{acting_reviewer}'. "
                    f"Approval requires an explicit, named human reviewer with governance authority."
                )
            self.reviewer_identity = acting_reviewer
            self.approval_notes = reason

        # Apply data update if authorized
        if data_update:
            # Deep merge update into payload
            self.payload.update(copy.deepcopy(data_update))

        self.state = new_state
        self._record_event(new_state, reason, actor)

        if new_state in (WorkflowStateEnum.COMMITTED, WorkflowStateEnum.REJECTED):
            self.is_terminal = True

        return self.state

    def get_state_snapshot(self) -> Dict[str, Any]:
        """Returns deterministic state snapshot without volatile fields."""
        snapshot = {
            "task_id": self.task_id,
            "request_id": self.request_id,
            "actor_id": self.actor_id,
            "current_state": self.state.value,
            "reviewer_identity": self.reviewer_identity,
            "approval_notes": self.approval_notes,
            "is_terminal": self.is_terminal,
            "payload": self.payload,
            "history_summary": [
                {"state": h["state"], "reason": h["reason"], "state_digest": h["state_digest"]}
                for h in self.history
            ],
        }
        return normalize_for_determinism(snapshot)

    def compute_current_state_hash(self) -> str:
        """Computes deterministic SHA-256 state hash."""
        return compute_sha256(self.get_state_snapshot())
