# Code Packet: State Machine & Event Sourcing Architecture

## Context & Standard
- **Standard**: SETU OS Architecture v6.0
- **Module**: `src/enterprise_core/state_machine.py` & `src/enterprise_core/determinism.py`
- **Integrations**: Gov-OS (Ledger) & Bucket (Audit)

## Deterministic Finite State Machine (FSM)

### 1. State Lifecycle Specification
```
[INTAKE] ──→ [POLICY_VALIDATION] ──→ [EVALUATION_PENDING] ──→ [AWAITING_REVIEW]
                                                                     │
                                                                     ▼
[COMMITTED] ←── [NIYANTRAN_DISPATCH] ←── [GOVERNED_APPROVAL] (or [REJECTED])
```

### 2. Invariant Protections
- **No State Jumps**: Transitions from `INTAKE` directly to `GOVERNED_APPROVAL` or `COMMITTED` are blocked with `StateTransitionError`.
- **Terminal Immutability**: States `COMMITTED` and `REJECTED` are terminal. Any subsequent write or transition attempt throws an immutable state violation error.
- **Append-Only Event Sourcing**: Every state change records an immutable event log containing previous state, new state, actor, reason, and SHA-256 digest of payload.

### 3. 50-Run Deterministic State Hashing
- Normalizer strips volatile fields (`timestamp`, `trace_id`, `pid`, `ephemeral_tokens`).
- Keys sorted recursively with canonical JSON serialization.
- 50 consecutive runs produce the identical state hash:
  `740c79a801044acd223bdf3c0e5fe868870d2911fc41623e94edbe4c176d2dd7`
