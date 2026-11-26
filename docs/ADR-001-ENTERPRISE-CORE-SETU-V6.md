# ADR-001: Enterprise Core Architecture & Integration Alignment under SETU OS v6.0

## Status
**ACCEPTED** - 2026-11-26

## Context
The BHIV Enterprise Operating System Common Core requires a government-grade review and operational core module (`T-OUT-OF-SYLLABUS`). Prior candidate evaluation (`CMO Agent V2`, task-ext-3a0ce21abe9a) received a PASS (100/100) verdict, but flagged `integration_fail` as a weakness focus. 

To prevent integration failures across the 6-pillar ecosystem (**BHIV Common Core**, **GC Shakti**, **Niyantran**, **Bucket**, **Gov-OS**, and **Saarthi**), this subsystem must enforce:
1. Strict schema validation (v1.0) with zero tolerance for schema drift (`extra="forbid"`).
2. Deterministic state transitions with immutable append-only state event logs.
3. 50-consecutive-run stability yielding identical SHA-256 state hashes.
4. Universal error boundaries guaranteeing zero unhandled 500 exceptions on malformed or malicious inputs.
5. Strict dependency pinning (`==`) complying with the BHIV PKB standard.

## Decision

### 1. Architectural Boundary & Separation of Concerns
The Enterprise Core will be implemented in `src/enterprise_core/` with clear domain boundaries:
- `contracts/schemas.py`: Canonical Schema v1.0 defining all data interchange models across the 6 pillars.
- `src/enterprise_core/state_machine.py`: Deterministic FSM governing proposal review, policy checks, managerial sign-off, and dispatch. Unauthorized direct state mutations are structurally prevented.
- `src/enterprise_core/determinism.py`: Normalization and hashing utility producing deterministic SHA-256 hashes by stripping volatile fields (`timestamp`, `trace_id`, `pid`, `ephemeral_tokens`) and sorting keys recursively.
- `src/enterprise_core/error_boundary.py`: Structured error interception middleware preventing 500 status codes, returning structured error contracts with error codes and sanitized messages.
- `src/enterprise_core/integrations/`: Dedicated adapters for each ecosystem block:
  - `shakti_adapter.py` (GC Shakti policy compliance)
  - `niyantran_adapter.py` (Niyantran workflow task assignment)
  - `bucket_adapter.py` (Bucket immutable audit storage)
  - `gov_os_adapter.py` (Gov-OS ledger and cryptographic attestation)
  - `saarthi_adapter.py` (Saarthi operational visibility)

### 2. Dependency Specification
All dependencies in `requirements.txt` are strictly pinned with `==` to prevent ABI conflicts and unpinned dependency creep.

### 3. Five-Tier Verification Matrix
Automated test suite under `tests/` structured into:
- Tier 1: Unit tests (Pydantic schema constraints, state transition immutability)
- Tier 2: Integration tests (Multi-pillar pipeline traversal from intake to dispatch)
- Tier 3: Determinism verification (50 consecutive runs producing identical SHA-256 digests)
- Tier 4: Negative & boundary tests (Malformed payloads, schema violations, duplicate approvals)
- Tier 5: Regression & ecosystem compatibility tests

## Consequences
- Guaranteed reproducibility of reviews and runtime audit trails.
- Complete operational defense against runtime 500 exceptions.
- Compliance with SETU OS Architecture v6.0.
