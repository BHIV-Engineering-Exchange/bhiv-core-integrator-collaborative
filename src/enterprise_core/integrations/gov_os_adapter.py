"""
src/enterprise_core/integrations/gov_os_adapter.py
=================================================
Gov-OS: Governance Ledger & Cryptographic Verification Adapter.
Maintains tamper-evident hash chaining and state attestation.
"""

from __future__ import annotations

import datetime
from typing import Dict, List, Optional
from contracts.schemas import (
    GovernanceLedgerEntry,
    CryptographicVerification,
    SCHEMA_VERSION,
)
from ..determinism import compute_sha256

GENESIS_HASH = "0" * 64


class GovOSLedgerAdapter:
    """Manages the Gov-OS cryptographic governance ledger."""

    def __init__(self):
        self.chain: List[GovernanceLedgerEntry] = []
        self._initialize_genesis()

    def _initialize_genesis(self) -> None:
        genesis_entry = GovernanceLedgerEntry(
            block_index=0,
            transaction_id="TX-GENESIS-GOV-OS",
            trace_id="TRC-GENESIS",
            task_id="GENESIS",
            state_hash=compute_sha256({"genesis": True, "standard": "SETU-OS-v6.0"}),
            previous_hash=GENESIS_HASH,
            timestamp="2026-01-01T00:00:00Z",
            recorded_by="GOV_OS_CORE_V6",
            status="COMMITTED",
            schema_version=SCHEMA_VERSION,
        )
        self.chain.append(genesis_entry)

    def commit_state_transition(
        self,
        task_id: str,
        transaction_id: str,
        trace_id: str,
        state_snapshot: Dict[str, Any],
    ) -> GovernanceLedgerEntry:
        """Appends a new block to the Gov-OS ledger with chained SHA-256 hash."""
        previous_block = self.chain[-1]
        state_hash = compute_sha256(state_snapshot)
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        entry = GovernanceLedgerEntry(
            block_index=len(self.chain),
            transaction_id=transaction_id,
            trace_id=trace_id,
            task_id=task_id,
            state_hash=state_hash,
            previous_hash=previous_block.state_hash,
            timestamp=now,
            recorded_by="GOV_OS_CORE_V6",
            status="COMMITTED",
            schema_version=SCHEMA_VERSION,
        )
        self.chain.append(entry)
        return entry

    def verify_ledger_integrity(self) -> bool:
        """Validates the cryptographic chain of all blocks."""
        for i in range(1, len(self.chain)):
            prev = self.chain[i - 1]
            curr = self.chain[i]
            if curr.previous_hash != prev.state_hash:
                return False
        return True

    def verify_state_attestation(self, state_hash: str) -> CryptographicVerification:
        """Checks if a state hash exists in the committed ledger."""
        for block in self.chain:
            if block.state_hash == state_hash:
                return CryptographicVerification(
                    is_valid=True,
                    state_hash=state_hash,
                    algorithm="SHA-256",
                    verified_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    ledger_block_index=block.block_index,
                )
        return CryptographicVerification(
            is_valid=False,
            state_hash=state_hash,
            algorithm="SHA-256",
            verified_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            ledger_block_index=-1,
        )
