"""
Tests for the evidence validation module.

Validates Governing Principle 2 (Evidence First):
  - Every node requires defined evidence before proceeding.
  - No evidence → no classification (returns invalid result).
"""

import pytest
from fraud_classifier.taxonomy import EvidenceType
from fraud_classifier.evidence import Evidence, validate_evidence_for_node


# ── Helpers ───────────────────────────────────────────────────────────────────


def make_evidence(et: EvidenceType, value: object = True) -> Evidence:
    return Evidence(evidence_type=et, value=value, source="test_system")


# ── Evidence dataclass tests ──────────────────────────────────────────────────


class TestEvidence:
    def test_valid_evidence_creation(self):
        e = make_evidence(EvidenceType.IDENTITY_MISMATCH)
        assert e.evidence_type == EvidenceType.IDENTITY_MISMATCH
        assert e.source == "test_system"
        assert e.metadata == {}

    def test_evidence_with_metadata(self):
        e = Evidence(
            evidence_type=EvidenceType.UNUSUAL_AMOUNT,
            value=5000.00,
            source="transaction_monitor",
            metadata={"threshold": 1000},
        )
        assert e.metadata["threshold"] == 1000

    def test_invalid_evidence_type_raises(self):
        with pytest.raises((ValueError, AttributeError)):
            Evidence(evidence_type="not_an_enum", value=True, source="test")  # type: ignore[arg-type]

    def test_empty_source_raises(self):
        with pytest.raises(ValueError, match="source"):
            Evidence(evidence_type=EvidenceType.IDENTITY_MISMATCH, value=True, source="")

    def test_whitespace_source_raises(self):
        with pytest.raises(ValueError, match="source"):
            Evidence(evidence_type=EvidenceType.IDENTITY_MISMATCH, value=True, source="   ")


# ── validate_evidence_for_node tests ─────────────────────────────────────────


class TestValidateEvidenceForNode:
    def test_root_node_always_valid(self):
        """Root node has no requirements; even empty evidence list is valid."""
        result = validate_evidence_for_node("root", [])
        assert result.is_valid is True
        assert result.missing_evidence == []

    def test_valid_evidence_for_internal_check(self):
        evidence = [
            make_evidence(EvidenceType.EMPLOYEE_ACCESS_ANOMALY),
            make_evidence(EvidenceType.INSIDER_PATTERN),
        ]
        result = validate_evidence_for_node("internal_check", evidence)
        assert result.is_valid is True
        assert result.missing_evidence == []

    def test_partial_evidence_invalid(self):
        """Only one of two required evidence types → invalid."""
        evidence = [make_evidence(EvidenceType.EMPLOYEE_ACCESS_ANOMALY)]
        result = validate_evidence_for_node("internal_check", evidence)
        assert result.is_valid is False
        assert EvidenceType.INSIDER_PATTERN in result.missing_evidence

    def test_no_evidence_invalid_for_node_with_requirements(self):
        result = validate_evidence_for_node("cnp_check", [])
        assert result.is_valid is False
        assert len(result.missing_evidence) > 0

    def test_extra_evidence_does_not_block(self):
        """Extra evidence beyond requirements should still pass validation."""
        evidence = [
            make_evidence(EvidenceType.EMPLOYEE_ACCESS_ANOMALY),
            make_evidence(EvidenceType.INSIDER_PATTERN),
            make_evidence(EvidenceType.BEHAVIORAL_ANOMALY),  # extra
        ]
        result = validate_evidence_for_node("internal_check", evidence)
        assert result.is_valid is True

    def test_unknown_node_returns_valid(self):
        """An unrecognised node name has no requirements → valid by default."""
        result = validate_evidence_for_node("nonexistent_node", [])
        assert result.is_valid is True

    def test_present_evidence_list_populated(self):
        evidence = [
            make_evidence(EvidenceType.CARD_NOT_PRESENT),
            make_evidence(EvidenceType.UNUSUAL_AMOUNT),
        ]
        result = validate_evidence_for_node("cnp_check", evidence)
        assert result.is_valid is True
        assert EvidenceType.CARD_NOT_PRESENT in result.present_evidence
        assert EvidenceType.UNUSUAL_AMOUNT in result.present_evidence
