# src/enterprise_core/integrations/__init__.py
"""
Integration adapters connecting Enterprise Core to the 6-pillar ecosystem.
"""

from .shakti_adapter import GCShaktiAdapter
from .niyantran_adapter import NiyantranAdapter
from .bucket_adapter import BucketAuditAdapter
from .gov_os_adapter import GovOSLedgerAdapter
from .saarthi_adapter import SaarthiTelemetryAdapter

__all__ = [
    "GCShaktiAdapter",
    "NiyantranAdapter",
    "BucketAuditAdapter",
    "GovOSLedgerAdapter",
    "SaarthiTelemetryAdapter",
]
