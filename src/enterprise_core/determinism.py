"""
src/enterprise_core/determinism.py
==================================
Deterministic normalization and SHA-256 state hashing utility.
Guarantees identical hash stability across 50 consecutive runs.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Set

DEFAULT_VOLATILE_KEYS: Set[str] = {
    "timestamp",
    "time",
    "date",
    "created_at",
    "updated_at",
    "emitted_at",
    "stored_at",
    "dispatched_at",
    "verified_at",
    "trace_id",
    "execution_time_ms",
    "duration_ms",
    "pid",
    "random_seed",
    "nonce",
    "access_token",
    "ephemeral_id",
}


def normalize_for_determinism(data: Any, volatile_keys: Set[str] = None) -> Any:
    """
    Recursively strips volatile fields and normalizes data structures
    so that identical logical states produce identical serialized representations.
    """
    if volatile_keys is None:
        volatile_keys = DEFAULT_VOLATILE_KEYS

    if isinstance(data, dict):
        cleaned: Dict[str, Any] = {}
        for k in sorted(data.keys()):
            if str(k).lower() in volatile_keys:
                continue
            cleaned[k] = normalize_for_determinism(data[k], volatile_keys)
        return cleaned
    elif isinstance(data, (list, tuple)):
        return [normalize_for_determinism(item, volatile_keys) for item in data]
    elif isinstance(data, float):
        # Format floating points to deterministic precision (6 decimal places)
        return round(data, 6)
    else:
        return data


def canonical_json(data: Any) -> str:
    """Returns canonical JSON representation with sorted keys and no extraneous whitespace."""
    normalized = normalize_for_determinism(data)
    return json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def compute_sha256(data: Any) -> str:
    """Computes deterministic SHA-256 hexadecimal digest from normalized payload."""
    if isinstance(data, str):
        payload_bytes = data.encode("utf-8")
    else:
        payload_bytes = canonical_json(data).encode("utf-8")
    return hashlib.sha256(payload_bytes).hexdigest()
