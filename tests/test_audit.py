"""
Tests for the audit logging module.

Validates Governing Principle 6 (Auditability):
  All paths, evidence, and overrides are logged.
"""

import pytest
from fraud_classifier.audit import AuditLogger, AuditRecord, get_audit_log, clear_audit_log


@pytest.fixture(autouse=True)
def reset_audit_log():
    """Clear the in-memory audit log before and after every test."""
    clear_audit_log()
    yield
    clear_audit_log()


class TestAuditRecord:
    def test_record_has_unique_id(self):
        r1 = AuditRecord(event_type="test", case_id="c1")
        r2 = AuditRecord(event_type="test", case_id="c2")
        assert r1.record_id != r2.record_id

    def test_record_has_timestamp(self):
        r = AuditRecord(event_type="classification", case_id="c1")
        assert r.timestamp  # non-empty ISO string

    def test_record_defaults(self):
        r = AuditRecord()
        assert r.node_path == []
        assert r.evidence_types == []
        assert r.extra == {}
        assert r.overridden_by is None
        assert r.category is None


class TestAuditLogger:
    def test_log_classification_creates_record(self):
        logger = AuditLogger()
        record = logger.log_classification(
            case_id="case-001",
            node_path=["root", "cnp_check"],
            category="card_not_present_fraud",
            confidence=0.85,
            evidence_types=["card_not_present", "unusual_amount"],
        )
        assert record.event_type == "classification"
        assert record.case_id == "case-001"
        assert record.category == "card_not_present_fraud"
        assert record.confidence == 0.85

    def test_log_escalation_creates_record(self):
        logger = AuditLogger()
        record = logger.log_escalation(
            case_id="case-002",
            node_path=["root", "internal_check"],
            reason="Human approval required",
            confidence=0.75,
            evidence_types=["employee_access_anomaly"],
        )
        assert record.event_type == "escalation"
        assert "Human approval required" in record.notes

    def test_log_human_override_records_reviewer(self):
        logger = AuditLogger()
        record = logger.log_human_override(
            case_id="case-003",
            node_path=["root", "first_party_check"],
            original_category="pending_human_review",
            override_category="first_party_fraud",
            overridden_by="analyst-42",
            justification="Customer admitted to the fraud.",
        )
        assert record.event_type == "human_override"
        assert record.overridden_by == "analyst-42"
        assert record.category == "first_party_fraud"
        assert "original_category" in record.extra

    def test_log_evidence_rejected_records_missing(self):
        logger = AuditLogger()
        record = logger.log_evidence_rejected(
            case_id="case-004",
            node="synthetic_identity_check",
            missing_evidence=["identity_mismatch", "synthetic_identity_indicators"],
        )
        assert record.event_type == "evidence_rejected"
        assert "identity_mismatch" in record.notes

    def test_log_error_records_message(self):
        logger = AuditLogger()
        record = logger.log_error(
            case_id="case-005",
            node_path=["root"],
            error="Unexpected null reference in evidence list",
        )
        assert record.event_type == "error"
        assert "null reference" in record.notes

    def test_custom_sink_is_called(self):
        collected: list[AuditRecord] = []

        def custom_sink(r: AuditRecord) -> None:
            collected.append(r)

        logger = AuditLogger(sink=custom_sink)
        logger.log_classification(
            case_id="c1",
            node_path=["root"],
            category="no_fraud",
            confidence=0.9,
            evidence_types=[],
        )
        assert len(collected) == 1
        assert collected[0].case_id == "c1"

    def test_default_sink_appends_to_global_log(self):
        logger = AuditLogger()
        logger.log_classification(
            case_id="c-global",
            node_path=["root"],
            category="no_fraud",
            confidence=0.9,
            evidence_types=[],
        )
        log = get_audit_log()
        assert any(r.case_id == "c-global" for r in log)

    def test_clear_audit_log_empties_store(self):
        logger = AuditLogger()
        logger.log_classification(
            case_id="temp",
            node_path=[],
            category="no_fraud",
            confidence=0.9,
            evidence_types=[],
        )
        clear_audit_log()
        assert get_audit_log() == []

    def test_node_path_is_copied(self):
        """Mutating the original path after logging should not affect the record."""
        logger = AuditLogger()
        path = ["root", "cnp_check"]
        record = logger.log_classification(
            case_id="c1",
            node_path=path,
            category="no_fraud",
            confidence=0.9,
            evidence_types=[],
        )
        path.append("mutated")
        assert "mutated" not in record.node_path
