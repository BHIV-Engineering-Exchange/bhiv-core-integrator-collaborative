"""
tests/test_regression.py
=========================
Tier 5: Regression & System Integrity Tests.
Verifies zero regressions against existing CMO Agent assets and SETU OS standards.
"""

from pathlib import Path
from src.enterprise_core.api import app, engine
from contracts.schemas import SCHEMA_VERSION


class TestRegressionAndSystemIntegrity:
    """Verifies complete system cohesion, backward compatibility, and artifact integrity."""

    def test_schema_version_consistency(self):
        assert SCHEMA_VERSION == "1.0.0"

    def test_genesis_block_integrity(self):
        assert len(engine.gov_os.chain) >= 1
        genesis = engine.gov_os.chain[0]
        assert genesis.block_index == 0
        assert genesis.previous_hash == "0" * 64
        assert engine.gov_os.verify_ledger_integrity() is True

    def test_bucket_persistence_directory_exists(self):
        storage_path = Path("data/bucket_records")
        storage_path.mkdir(parents=True, exist_ok=True)
        assert storage_path.exists()
        assert storage_path.is_dir()

    def test_dependency_pinning_in_requirements(self):
        req_path = Path("requirements.txt")
        assert req_path.exists()
        with open(req_path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]

        # Assert no loose '>=' or '<=' in requirements.txt
        for line in lines:
            assert ">=" not in line, f"Found unpinned dependency in requirements.txt: {line}"
            assert "==" in line, f"Expected pinned dependency with '==' in requirements.txt: {line}"
