# Code Packet: Routing, API & Security Middleware

## Context & Architecture
- **Standard**: SETU OS Architecture v6.0
- **Service**: BHIV Enterprise Operating System Common Core
- **Framework**: FastAPI (Pinned `fastapi==0.115.8`, `pydantic==2.13.3`)

## Architecture & Middleware Design

### 1. Strict Schema Enforcement Boundary
All inbound and outbound payloads are governed by `contracts/schemas.py`:
- `model_config = ConfigDict(extra="forbid", strict=True)`: Rejects any extraneous fields, preventing parameter tampering, prototype pollution, and schema drift.
- Strong regex validation on canonical IDs (`task_id`, `request_id`, `trace_id`).
- Immutable frozen records for ledger blocks and evidence envelopes.

### 2. Universal Error Boundary & Exception Interceptor
Implemented in `src/enterprise_core/error_boundary.py`:
- Catches `RequestValidationError`, `ValidationError`, `StateTransitionError`, `ValueError`, `KeyError`, and unexpected system runtime exceptions.
- Zero unhandled 500 exceptions exposed to callers.
- Canonical error responses:
  ```json
  {
    "status": "ERROR",
    "error_code": "SCHEMA_VALIDATION_ERROR",
    "status_code": 422,
    "message": "Inbound payload failed Schema v1.0 validation...",
    "trace_id": "TRC-ERR-XYZ",
    "schema_version": "1.0.0"
  }
  ```

### 3. Reviewer Identity Integrity Defense
- Structural check prohibits empty strings or default placeholders (`Prof_Evaluator`, `anonymous`, `evaluator`).
- Mandates explicit named human reviewers with operational authority (`Pratik Bhuwad - Product Owner`).
