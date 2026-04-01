"""
Tests for the explainability module.

Validates Governing Principle 5 (Explainability):
  Every classification must answer:
    1. Why this node?
    2. What evidence?
    3. What would change the decision?
"""

import pytest
from fraud_classifier.taxonomy import EvidenceType, FraudCategory, ConfidenceLevel
from fraud_classifier.evidence import Evidence
from fraud_classifier.confidence import calculate_confidence, ConfidenceResult
from fraud_classifier.explainer import build_explanation, Explanation


def make_evidence(et: EvidenceType, value: object = True) -> Evidence:
    return Evidence(evidence_type=et, value=value, source="test_system")


def make_high_confidence_evidence() -> list[Evidence]:
    return [
        make_evidence(EvidenceType.EMPLOYEE_ACCESS_ANOMALY),
        make_evidence(EvidenceType.INSIDER_PATTERN),
        make_evidence(EvidenceType.BEHAVIORAL_ANOMALY),
    ]


class TestBuildExplanation:
    def test_explanation_has_why_this_node(self):
        evidence = make_high_confidence_evidence()
        confidence = calculate_confidence(evidence)
        exp = build_explanation(
            node_path=["root", "internal_check"],
            final_node="internal_check",
            category=FraudCategory.INTERNAL_FRAUD,
            evidence_list=evidence,
            confidence=confidence,
        )
        assert isinstance(exp.why_this_node, str)
        assert len(exp.why_this_node) > 0
        assert "internal_check" in exp.why_this_node

    def test_explanation_node_path_included_in_why(self):
        evidence = make_high_confidence_evidence()
        confidence = calculate_confidence(evidence)
        exp = build_explanation(
            node_path=["root", "internal_check"],
            final_node="internal_check",
            category=FraudCategory.INTERNAL_FRAUD,
            evidence_list=evidence,
            confidence=confidence,
        )
        assert "root" in exp.why_this_node or "root → internal_check" in exp.why_this_node

    def test_explanation_has_evidence_summary(self):
        evidence = make_high_confidence_evidence()
        confidence = calculate_confidence(evidence)
        exp = build_explanation(
            node_path=["root", "internal_check"],
            final_node="internal_check",
            category=FraudCategory.INTERNAL_FRAUD,
            evidence_list=evidence,
            confidence=confidence,
        )
        assert isinstance(exp.evidence_summary, list)
        assert len(exp.evidence_summary) == len(evidence)

    def test_evidence_summary_contains_type_value_source(self):
        evidence = [make_evidence(EvidenceType.IDENTITY_MISMATCH, value=0.95)]
        confidence = calculate_confidence(evidence)
        exp = build_explanation(
            node_path=["root", "identity_check"],
            final_node="identity_check",
            category=FraudCategory.ACCOUNT_TAKEOVER,
            evidence_list=evidence,
            confidence=confidence,
        )
        assert any(
            item["type"] == EvidenceType.IDENTITY_MISMATCH.value
            for item in exp.evidence_summary
        )
        summary_item = exp.evidence_summary[0]
        assert "type" in summary_item
        assert "value" in summary_item
        assert "source" in summary_item
        assert "weight" in summary_item

    def test_explanation_has_counterfactuals(self):
        evidence = make_high_confidence_evidence()
        confidence = calculate_confidence(evidence)
        exp = build_explanation(
            node_path=["root", "internal_check"],
            final_node="internal_check",
            category=FraudCategory.INTERNAL_FRAUD,
            evidence_list=evidence,
            confidence=confidence,
        )
        assert isinstance(exp.counterfactuals, list)
        assert len(exp.counterfactuals) > 0
        for cf in exp.counterfactuals:
            assert isinstance(cf, str) and len(cf) > 0

    def test_explanation_has_confidence_breakdown(self):
        evidence = make_high_confidence_evidence()
        confidence = calculate_confidence(evidence)
        exp = build_explanation(
            node_path=["root", "internal_check"],
            final_node="internal_check",
            category=FraudCategory.INTERNAL_FRAUD,
            evidence_list=evidence,
            confidence=confidence,
        )
        bd = exp.confidence_breakdown
        assert "score" in bd
        assert "level" in bd
        assert "threshold_high" in bd
        assert "contributing_evidence" in bd

    def test_explanation_node_path_stored(self):
        evidence = make_high_confidence_evidence()
        confidence = calculate_confidence(evidence)
        path = ["root", "internal_check"]
        exp = build_explanation(
            node_path=path,
            final_node="internal_check",
            category=FraudCategory.INTERNAL_FRAUD,
            evidence_list=evidence,
            confidence=confidence,
        )
        assert exp.node_path == path

    def test_insufficient_evidence_counterfactual(self):
        """When category is INSUFFICIENT_EVIDENCE, counterfactuals mention missing evidence."""
        evidence = [make_evidence(EvidenceType.IDENTITY_MISMATCH)]
        confidence = calculate_confidence(evidence)
        exp = build_explanation(
            node_path=["root", "synthetic_identity_check"],
            final_node="synthetic_identity_check",
            category=FraudCategory.INSUFFICIENT_EVIDENCE,
            evidence_list=evidence,
            confidence=confidence,
        )
        assert any("missing" in cf.lower() or "evidence" in cf.lower() for cf in exp.counterfactuals)

    def test_medium_confidence_counterfactual_mentions_review(self):
        evidence = [
            make_evidence(EvidenceType.UNUSUAL_AMOUNT),
            make_evidence(EvidenceType.UNUSUAL_LOCATION),
            make_evidence(EvidenceType.NEW_PAYEE),
        ]
        confidence = calculate_confidence(evidence)
        assert confidence.level == ConfidenceLevel.MEDIUM
        exp = build_explanation(
            node_path=["root", "cnp_check"],
            final_node="cnp_check",
            category=FraudCategory.PENDING_HUMAN_REVIEW,
            evidence_list=evidence,
            confidence=confidence,
        )
        combined = " ".join(exp.counterfactuals).lower()
        assert "confidence" in combined or "review" in combined or "evidence" in combined
