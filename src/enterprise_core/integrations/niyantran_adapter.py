"""
src/enterprise_core/integrations/niyantran_adapter.py
====================================================
Niyantran: Task Assignment & Workflow Lifecycle Engine Adapter.
Handles zero-context-switch canonical task assignments without placeholder IDs.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict
from contracts.schemas import (
    TaskAssignmentRequest,
    TaskAssignmentResponse,
    SCHEMA_VERSION,
)


class NiyantranAdapter:
    """Dispatches verified assignments into the Niyantran orchestration engine."""

    def __init__(self):
        self.dispatched_registry: Dict[str, TaskAssignmentResponse] = {}

    def dispatch_assignment(self, request: TaskAssignmentRequest, trace_id: str) -> TaskAssignmentResponse:
        """
        Dispatches a canonical task assignment.
        Enforces canonical depth: specs must not contain placeholder values.
        """
        # Validate that spec does not contain placeholder strings
        spec_str = str(request.spec_payload).lower()
        if "placeholder" in spec_str or "todo" in spec_str or "tbd" in spec_str:
            raise ValueError(
                f"Niyantran Canonical Depth Violation: Task assignment '{request.task_id}' contains placeholder or TBD tokens in spec."
            )

        assignment_id = f"ASN-{request.task_id}-NTR"
        dispatched_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        response = TaskAssignmentResponse(
            assignment_id=assignment_id,
            task_id=request.task_id,
            target_agent=request.target_agent,
            status="ASSIGNED",
            dispatched_at=dispatched_at,
            trace_id=trace_id,
            schema_version=SCHEMA_VERSION,
        )
        self.dispatched_registry[assignment_id] = response
        return response
