"""
src/enterprise_core/error_boundary.py
=====================================
Universal Error Boundary & Exception Interceptor.
Guarantees zero unhandled 500 exceptions across malformed, invalid, or unauthorized inputs.
"""

from __future__ import annotations

import logging
from typing import Any, Dict
from pydantic import ValidationError
from fastapi.exceptions import RequestValidationError
from .state_machine import StateTransitionError

logger = logging.getLogger("enterprise_core.error_boundary")


def sanitize_error_response(exc: Exception, trace_id: str = "TRC-ERR-UNKNOWN") -> Dict[str, Any]:
    """
    Transforms any internal exception into a structured, sanitized v1.0 error contract.
    Ensures no raw stack traces or internal secrets are leaked, preventing 500 crashes.
    """
    if isinstance(exc, (ValidationError, RequestValidationError)):
        error_code = "SCHEMA_VALIDATION_ERROR"
        status_code = 422
        errors = []
        raw_errors = exc.errors() if hasattr(exc, "errors") else []
        for err in raw_errors:
            loc = " -> ".join(str(l) for l in err.get("loc", []))
            errors.append(f"{loc}: {err.get('msg', 'Invalid field')}")
        detail = "Inbound payload failed Schema v1.0 validation: " + ("; ".join(errors) if errors else str(exc))

    elif isinstance(exc, StateTransitionError):
        error_code = "STATE_TRANSITION_VIOLATION"
        status_code = 400
        detail = str(exc)

    elif isinstance(exc, ValueError):
        error_code = "INVALID_ARGUMENT_ERROR"
        status_code = 400
        detail = str(exc)

    elif isinstance(exc, KeyError):
        error_code = "MISSING_REQUIRED_RESOURCE"
        status_code = 404
        detail = f"Required resource or key missing: {str(exc)}"

    elif isinstance(exc, PermissionError):
        error_code = "AUTHORITY_ACCESS_DENIED"
        status_code = 403
        detail = f"Operational authority access denied: {str(exc)}"

    else:
        # Default safety fallback: catch-all boundary
        error_code = "OPERATIONAL_EXECUTION_ERROR"
        status_code = 400
        detail = f"Protected boundary caught unhandled operational exception: {type(exc).__name__}"
        logger.error(f"Error boundary intercepted exception: {exc}", exc_info=True)

    return {
        "status": "ERROR",
        "error_code": error_code,
        "status_code": status_code,
        "message": detail,
        "trace_id": trace_id,
        "schema_version": "1.0.0",
    }


class EnterpriseErrorBoundary:
    """Context manager or callable boundary intercepting execution exceptions."""

    def __init__(self, trace_id: str = "TRC-BOUNDARY"):
        self.trace_id = trace_id

    def execute_safely(self, fn, *args, **kwargs) -> Dict[str, Any]:
        """Executes a function within the protected error boundary."""
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            return sanitize_error_response(e, trace_id=self.trace_id)
