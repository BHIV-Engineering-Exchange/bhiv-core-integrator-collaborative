"""
src/enterprise_core/integrations/saarthi_adapter.py
==================================================
Saarthi: Visibility Layer & Operational Oversight Adapter.
Emits real-time telemetry, transition events, and leadership dashboard metrics.
"""

from __future__ import annotations

import datetime
from typing import Dict, List
from contracts.schemas import SaarthiTelemetryEvent


class SaarthiTelemetryAdapter:
    """Publishes operational events to the Saarthi visibility surface."""

    def __init__(self):
        self.events: List[SaarthiTelemetryEvent] = []

    def emit_metric(
        self,
        event_name: str,
        metric_type: str,
        value: float,
        trace_id: str,
        tags: Dict[str, str] = None,
    ) -> SaarthiTelemetryEvent:
        """Records a live telemetry event."""
        event_id = f"EVT-SAARTHI-{len(self.events) + 1:04d}"
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        event = SaarthiTelemetryEvent(
            event_id=event_id,
            event_name=event_name,
            metric_type=metric_type,
            value=float(value),
            trace_id=trace_id,
            tags=tags or {},
            emitted_at=now,
        )
        self.events.append(event)
        return event

    def get_latest_metrics(self) -> List[Dict[str, Any]]:
        """Returns recent metrics for dashboard rendering."""
        return [e.model_dump() for e in self.events[-50:]]
