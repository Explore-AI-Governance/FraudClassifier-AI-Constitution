"""
Audit logging module.

Enforces Governing Principle 6 – Auditability:
  "All paths, evidence, and overrides are logged."

Every classification, escalation, human override, and error is written to an
append-only in-process audit log.  Callers may supply a custom sink (e.g. a
database writer or a structured logger) by passing a ``log_sink`` callable to
:func:`get_audit_logger`.
"""

from __future__ import annotations

import datetime
import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class AuditRecord:
    """
    A single immutable audit event.

    Attributes:
        record_id:     UUID for this record.
        timestamp:     ISO-8601 UTC timestamp when the event occurred.
        event_type:    One of: ``classification``, ``escalation``,
                       ``human_override``, ``evidence_rejected``, ``error``.
        case_id:       Identifier of the fraud case being evaluated.
        node_path:     Decision-tree nodes traversed so far.
        category:      Classification outcome (may be ``None`` for partial events).
        confidence:    Confidence score (``None`` for non-classification events).
        evidence_types: List of evidence type names present on the case.
        overridden_by:  Human reviewer ID when this is an override event.
        notes:          Free-form notes (e.g. override justification).
        extra:          Additional structured metadata.
    """

    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
    event_type: str = ""
    case_id: str = ""
    node_path: list[str] = field(default_factory=list)
    category: str | None = None
    confidence: float | None = None
    evidence_types: list[str] = field(default_factory=list)
    overridden_by: str | None = None
    notes: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


# ── Audit logger ─────────────────────────────────────────────────────────────

# Type alias for a log-sink callable.
LogSink = Callable[[AuditRecord], None]

# Module-level in-memory store (useful for tests and simple deployments).
_audit_log: list[AuditRecord] = []


def _default_sink(record: AuditRecord) -> None:
    """Write the record to the Python logging system and in-memory store."""
    _audit_log.append(record)
    logger.info("AUDIT %s", json.dumps(asdict(record), default=str))


class AuditLogger:
    """
    Thin audit-logging facade used throughout the classifier.

    Parameters
    ----------
    sink:
        Callable invoked with each :class:`AuditRecord`.  Defaults to the
        built-in in-memory + Python logging sink.
    """

    def __init__(self, sink: LogSink | None = None) -> None:
        self._sink: LogSink = sink or _default_sink

    # ── Public helpers ────────────────────────────────────────────────────────

    def log_classification(
        self,
        *,
        case_id: str,
        node_path: list[str],
        category: str,
        confidence: float,
        evidence_types: list[str],
        notes: str = "",
        extra: dict[str, Any] | None = None,
    ) -> AuditRecord:
        return self._emit(
            event_type="classification",
            case_id=case_id,
            node_path=node_path,
            category=category,
            confidence=confidence,
            evidence_types=evidence_types,
            notes=notes,
            extra=extra or {},
        )

    def log_escalation(
        self,
        *,
        case_id: str,
        node_path: list[str],
        reason: str,
        confidence: float,
        evidence_types: list[str],
        extra: dict[str, Any] | None = None,
    ) -> AuditRecord:
        return self._emit(
            event_type="escalation",
            case_id=case_id,
            node_path=node_path,
            category=None,
            confidence=confidence,
            evidence_types=evidence_types,
            notes=reason,
            extra=extra or {},
        )

    def log_human_override(
        self,
        *,
        case_id: str,
        node_path: list[str],
        original_category: str,
        override_category: str,
        overridden_by: str,
        justification: str,
        extra: dict[str, Any] | None = None,
    ) -> AuditRecord:
        return self._emit(
            event_type="human_override",
            case_id=case_id,
            node_path=node_path,
            category=override_category,
            confidence=None,
            evidence_types=[],
            overridden_by=overridden_by,
            notes=justification,
            extra={"original_category": original_category, **(extra or {})},
        )

    def log_evidence_rejected(
        self,
        *,
        case_id: str,
        node: str,
        missing_evidence: list[str],
        extra: dict[str, Any] | None = None,
    ) -> AuditRecord:
        return self._emit(
            event_type="evidence_rejected",
            case_id=case_id,
            node_path=[node],
            category=None,
            confidence=None,
            evidence_types=[],
            notes=f"Missing required evidence: {', '.join(missing_evidence)}",
            extra=extra or {},
        )

    def log_error(
        self,
        *,
        case_id: str,
        node_path: list[str],
        error: str,
        extra: dict[str, Any] | None = None,
    ) -> AuditRecord:
        return self._emit(
            event_type="error",
            case_id=case_id,
            node_path=node_path,
            category=None,
            confidence=None,
            evidence_types=[],
            notes=error,
            extra=extra or {},
        )

    # ── Private ───────────────────────────────────────────────────────────────

    def _emit(
        self,
        *,
        event_type: str,
        case_id: str,
        node_path: list[str],
        category: str | None,
        confidence: float | None,
        evidence_types: list[str],
        overridden_by: str | None = None,
        notes: str = "",
        extra: dict[str, Any] | None = None,
    ) -> AuditRecord:
        record = AuditRecord(
            event_type=event_type,
            case_id=case_id,
            node_path=list(node_path),
            category=category,
            confidence=confidence,
            evidence_types=list(evidence_types),
            overridden_by=overridden_by,
            notes=notes,
            extra=extra or {},
        )
        self._sink(record)
        return record


def get_audit_log() -> list[AuditRecord]:
    """Return the accumulated in-memory audit log (read-only snapshot)."""
    return list(_audit_log)


def clear_audit_log() -> None:
    """Clear the in-memory audit log (useful in tests)."""
    _audit_log.clear()
