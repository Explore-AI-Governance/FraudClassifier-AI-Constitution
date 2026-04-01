"""
Tests for the confidence scoring and escalation module.

Validates Governing Principle 3 (Confidence & Escalation):
  - High confidence (≥0.70)   → classify
  - Medium confidence (≥0.40) → flag for review
  - Low confidence (<0.40)    → human decision
"""

import pytest
from fraud_classifier.taxonomy import EvidenceType, ConfidenceLevel
from fraud_classifier.evidence import Evidence
from fraud_classifier.confidence import (
    calculate_confidence,
    should_escalate,
    EVIDENCE_WEIGHTS,
    HIGH_CONFIDENCE_THRESHOLD,
    MEDIUM_CONFIDENCE_THRESHOLD,
)


def make_evidence(et: EvidenceType) -> Evidence:
    return Evidence(evidence_type=et, value=True, source="test")


class TestCalculateConfidence:
    def test_empty_evidence_low_confidence(self):
        result = calculate_confidence([])
        assert result.score == 0.0
        assert result.level == ConfidenceLevel.LOW

    def test_high_confidence_classification(self):
        """Enough strong evidence should yield HIGH confidence."""
        evidence = [
            make_evidence(EvidenceType.IDENTITY_MISMATCH),          # 0.30
            make_evidence(EvidenceType.DEVICE_FINGERPRINT_ANOMALY), # 0.25
            make_evidence(EvidenceType.SYNTHETIC_IDENTITY_INDICATORS),  # 0.35
        ]
        result = calculate_confidence(evidence)
        assert result.score >= HIGH_CONFIDENCE_THRESHOLD
        assert result.level == ConfidenceLevel.HIGH

    def test_medium_confidence_range(self):
        """Evidence that sums between 0.40 and 0.70 → MEDIUM."""
        evidence = [
            make_evidence(EvidenceType.UNUSUAL_AMOUNT),   # 0.20
            make_evidence(EvidenceType.UNUSUAL_LOCATION), # 0.15
            make_evidence(EvidenceType.NEW_PAYEE),        # 0.15
        ]
        result = calculate_confidence(evidence)
        assert MEDIUM_CONFIDENCE_THRESHOLD <= result.score < HIGH_CONFIDENCE_THRESHOLD
        assert result.level == ConfidenceLevel.MEDIUM

    def test_low_confidence_range(self):
        evidence = [make_evidence(EvidenceType.NEW_PAYEE)]  # 0.15
        result = calculate_confidence(evidence)
        assert result.score < MEDIUM_CONFIDENCE_THRESHOLD
        assert result.level == ConfidenceLevel.LOW

    def test_score_capped_at_one(self):
        """Score must never exceed 1.0 even with many signals."""
        evidence = [make_evidence(et) for et in EvidenceType]
        result = calculate_confidence(evidence)
        assert result.score <= 1.0

    def test_contributing_evidence_recorded(self):
        evidence = [
            make_evidence(EvidenceType.IDENTITY_MISMATCH),
            make_evidence(EvidenceType.UNUSUAL_AMOUNT),
        ]
        result = calculate_confidence(evidence)
        assert EvidenceType.IDENTITY_MISMATCH in result.contributing_evidence
        assert EvidenceType.UNUSUAL_AMOUNT in result.contributing_evidence

    def test_score_is_rounded(self):
        evidence = [make_evidence(EvidenceType.IDENTITY_MISMATCH)]
        result = calculate_confidence(evidence)
        # Score should have at most 4 decimal places
        assert result.score == round(result.score, 4)

    def test_all_evidence_weights_are_positive(self):
        for et, w in EVIDENCE_WEIGHTS.items():
            assert w > 0, f"Weight for {et} should be positive"


class TestShouldEscalate:
    def test_high_confidence_does_not_escalate(self):
        evidence = [
            make_evidence(EvidenceType.IDENTITY_MISMATCH),
            make_evidence(EvidenceType.SYNTHETIC_IDENTITY_INDICATORS),
            make_evidence(EvidenceType.DEVICE_FINGERPRINT_ANOMALY),
        ]
        confidence = calculate_confidence(evidence)
        assert confidence.level == ConfidenceLevel.HIGH
        assert should_escalate(confidence) is False

    def test_medium_confidence_escalates(self):
        evidence = [
            make_evidence(EvidenceType.UNUSUAL_AMOUNT),
            make_evidence(EvidenceType.UNUSUAL_LOCATION),
            make_evidence(EvidenceType.NEW_PAYEE),
        ]
        confidence = calculate_confidence(evidence)
        assert confidence.level == ConfidenceLevel.MEDIUM
        assert should_escalate(confidence) is True

    def test_low_confidence_escalates(self):
        confidence = calculate_confidence([])
        assert confidence.level == ConfidenceLevel.LOW
        assert should_escalate(confidence) is True
