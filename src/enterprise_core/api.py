"""
src/enterprise_core/api.py
==========================
FastAPI Application for BHIV Enterprise Core (SETU OS Architecture v6.0).
Exposes governed operational endpoints with strict Schema v1.0 enforcement.
"""

from __future__ import annotations

import logging
from typing import Any, Dict
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field

from contracts.schemas import (
    CoreOperationalRequest,
    CoreOperationalResponse,
    SCHEMA_VERSION,
)
from .core_engine import EnterpriseCoreEngine
from .error_boundary import sanitize_error_response

logger = logging.getLogger("enterprise_core.api")

app = FastAPI(
    title="BHIV Enterprise Operating System Common Core",
    description="Government-grade operational review and engineering platform under SETU OS Architecture v6.0",
    version=SCHEMA_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = EnterpriseCoreEngine()


class ApprovalRequestPayload(BaseModel):
    request_id: str = Field(..., min_length=4)
    reviewer_name: str = Field(..., min_length=2)
    decision_notes: str = Field(..., min_length=5)


class DispatchRequestPayload(BaseModel):
    request_id: str = Field(..., min_length=4)
    target_agent: str = Field(..., min_length=2)
    title: str = Field(..., min_length=5)
    calibrated_duration_mins: int = Field(180, ge=15, le=1440)


# Global Exception Handlers (idiomatic FastAPI, zero hanging middleware)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    trace_id = request.headers.get("X-Trace-Id", "TRC-VALIDATION-ERR")
    sanitized = sanitize_error_response(exc, trace_id=trace_id)
    return JSONResponse(status_code=422, content=sanitized)


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    trace_id = request.headers.get("X-Trace-Id", "TRC-UNHANDLED-ERR")
    sanitized = sanitize_error_response(exc, trace_id=trace_id)
    return JSONResponse(status_code=sanitized.get("status_code", 400), content=sanitized)


@app.get("/health")
def health_check():
    return {
        "status": "HEALTHY",
        "service": "BHIV Enterprise Operating System Common Core",
        "standard": "SETU OS Architecture v6.0",
        "schema_version": SCHEMA_VERSION,
        "active_workflows_count": len(engine.active_workflows),
    }


@app.get("/status")
def system_status():
    return {
        "status": "OPERATIONAL",
        "ledger_blocks_count": len(engine.gov_os.chain),
        "ledger_integrity": engine.gov_os.verify_ledger_integrity(),
        "recent_telemetry_events": len(engine.saarthi.events),
        "schema_version": SCHEMA_VERSION,
    }


@app.post("/v1/core/review/submit", response_model=CoreOperationalResponse)
def submit_review_intake(payload: CoreOperationalRequest):
    return engine.process_intake(payload)


@app.post("/v1/core/review/evaluate")
def evaluate_compliance(request_id: str, policy_id: str = "POL-ENTERPRISE-001"):
    return engine.evaluate_policy_compliance(request_id=request_id, policy_id=policy_id)


@app.post("/v1/core/review/approve")
def approve_review(payload: ApprovalRequestPayload):
    return engine.execute_governed_approval(
        request_id=payload.request_id,
        reviewer_name=payload.reviewer_name,
        decision_notes=payload.decision_notes,
    )


@app.post("/v1/core/assignment/dispatch")
def dispatch_assignment(payload: DispatchRequestPayload):
    return engine.dispatch_to_niyantran(
        request_id=payload.request_id,
        target_agent=payload.target_agent,
        title=payload.title,
        calibrated_duration_mins=payload.calibrated_duration_mins,
    )


@app.get("/v1/core/governance/audit/{request_id}")
def get_governance_audit(request_id: str):
    if request_id not in engine.active_workflows:
        raise KeyError(f"Workflow {request_id} not found")
    fsm = engine.active_workflows[request_id]
    return {
        "task_id": fsm.task_id,
        "request_id": fsm.request_id,
        "current_state": fsm.state.value,
        "state_hash": fsm.compute_current_state_hash(),
        "history": fsm.history,
        "state_snapshot": fsm.get_state_snapshot(),
    }
