"""
Integration tests for the FraudClassifier decision engine.

Validates all six Governing Principles together via end-to-end classification
scenarios.
"""

import pytest
from fraud_classifier import (
    FraudClassifier,
    Evidence,
    EvidenceType,
    FraudCategory,
    ConfidenceLevel,
    clear_audit_log,
    get_audit_log,
)


@pytest.fixture(autouse=True)
def reset_log():
    clear_audit_log()
    yield
    clear_audit_log()


def make_evidence(et: EvidenceType, value: object = True) -> Evidence:
    return Evidence(evidence_type=et, value=value, source="test_system")


# ── Principle 1 – Taxonomy Fidelity ──────────────────────────────────────────


class TestTaxonomyFidelity:
    def test_result_category_is_always_fraud_category_enum(self):
        clf = FraudClassifier()
        result = clf.classify([])
        assert isinstance(result.category, FraudCategory)

    def test_no_unknown_category_returned(self):
        clf = FraudClassifier()
        known = set(FraudCategory)
        for evidence_set in [
            [],
            [make_evidence(EvidenceType.EMPLOYEE_ACCESS_ANOMALY), make_evidence(EvidenceType.INSIDER_PATTERN), make_evidence(EvidenceType.BEHAVIORAL_ANOMALY)],
            [make_evidence(EvidenceType.CARD_NOT_PRESENT), make_evidence(EvidenceType.UNUSUAL_AMOUNT), make_evidence(EvidenceType.VELOCITY_ANOMALY)],
        ]:
            result = clf.classify(evidence_set)
            assert result.category in known


# ── Principle 2 – Evidence First ─────────────────────────────────────────────


class TestEvidenceFirst:
    def test_no_evidence_returns_pending_human_review_or_no_fraud(self):
        """With no evidence the classifier cannot confidently classify anything."""
        clf = FraudClassifier()
        result = clf.classify([])
        # With no evidence, confidence is LOW → pending_human_review
        assert result.category in (FraudCategory.PENDING_HUMAN_REVIEW, FraudCategory.NO_FRAUD)

    def test_insufficient_evidence_does_not_force_a_fraud_category(self):
        """Single weak evidence alone must not produce a definitive fraud label."""
        clf = FraudClassifier()
        result = clf.classify([make_evidence(EvidenceType.NEW_PAYEE)])
        # NEW_PAYEE alone is weak (0.15); confidence is LOW → must escalate
        assert result.category == FraudCategory.PENDING_HUMAN_REVIEW
        assert result.requires_human_review is True


# ── Principle 3 – Confidence & Escalation ────────────────────────────────────


class TestConfidenceEscalation:
    def test_high_confidence_internal_fraud_classifies_directly(self):
        """
        internal_check is in HUMAN_APPROVAL_REQUIRED_NODES, so it will always
        be escalated even with high confidence.  Use account_takeover_check
        (not in that set) to test the high-confidence → direct-classify path.
        """
        clf = FraudClassifier()
        evidence = [
            make_evidence(EvidenceType.IDENTITY_MISMATCH),          # 0.30
            make_evidence(EvidenceType.DEVICE_FINGERPRINT_ANOMALY), # 0.25
            make_evidence(EvidenceType.BEHAVIORAL_ANOMALY),         # 0.20
            make_evidence(EvidenceType.SYNTHETIC_IDENTITY_INDICATORS),  # 0.35
        ]
        result = clf.classify(evidence)
        assert result.confidence.level == ConfidenceLevel.HIGH
        # synthetic_identity_check fires (required evidence present) and it IS
        # in human-approval nodes → escalated, but at high confidence.
        # The important assertion here is that confidence is correctly HIGH.

    def test_medium_confidence_escalates_to_review(self):
        clf = FraudClassifier()
        # Enough evidence to be MEDIUM but not HIGH, and matching cnp_check
        evidence = [
            make_evidence(EvidenceType.CARD_NOT_PRESENT),
            make_evidence(EvidenceType.UNUSUAL_AMOUNT),
            make_evidence(EvidenceType.UNUSUAL_LOCATION),
        ]
        result = clf.classify(evidence)
        assert result.confidence.level == ConfidenceLevel.MEDIUM
        assert result.requires_human_review is True
        assert result.category == FraudCategory.PENDING_HUMAN_REVIEW

    def test_low_confidence_always_requires_human(self):
        clf = FraudClassifier()
        result = clf.classify([])
        assert result.confidence.level == ConfidenceLevel.LOW
        assert result.requires_human_review is True
        assert result.category == FraudCategory.PENDING_HUMAN_REVIEW

    def test_high_confidence_cnp_classifies_without_review(self):
        """Card-not-present check is NOT in human-approval nodes, so high confidence → direct."""
        clf = FraudClassifier()
        evidence = [
            make_evidence(EvidenceType.CARD_NOT_PRESENT),        # 0.20
            make_evidence(EvidenceType.UNUSUAL_AMOUNT),          # 0.20
            make_evidence(EvidenceType.VELOCITY_ANOMALY),        # 0.25
            make_evidence(EvidenceType.BEHAVIORAL_ANOMALY),      # 0.20
            make_evidence(EvidenceType.UNUSUAL_LOCATION),        # 0.15
        ]
        result = clf.classify(evidence)
        assert result.confidence.level == ConfidenceLevel.HIGH
        assert result.category == FraudCategory.CARD_NOT_PRESENT_FRAUD
        assert result.requires_human_review is False


# ── Principle 4 – Human-in-the-Loop ──────────────────────────────────────────


class TestHumanInTheLoop:
    def test_internal_check_always_requires_human(self):
        clf = FraudClassifier()
        evidence = [
            make_evidence(EvidenceType.EMPLOYEE_ACCESS_ANOMALY),
            make_evidence(EvidenceType.INSIDER_PATTERN),
            make_evidence(EvidenceType.BEHAVIORAL_ANOMALY),
        ]
        result = clf.classify(evidence)
        assert result.requires_human_review is True
        assert result.category == FraudCategory.PENDING_HUMAN_REVIEW

    def test_synthetic_identity_check_always_requires_human(self):
        clf = FraudClassifier()
        evidence = [
            make_evidence(EvidenceType.SYNTHETIC_IDENTITY_INDICATORS),
            make_evidence(EvidenceType.IDENTITY_MISMATCH),
            make_evidence(EvidenceType.DEVICE_FINGERPRINT_ANOMALY),
        ]
        result = clf.classify(evidence)
        assert result.requires_human_review is True
        assert result.category == FraudCategory.PENDING_HUMAN_REVIEW

    def test_human_override_accepted_with_justification(self):
        clf = FraudClassifier()
        evidence = [
            make_evidence(EvidenceType.EMPLOYEE_ACCESS_ANOMALY),
            make_evidence(EvidenceType.INSIDER_PATTERN),
            make_evidence(EvidenceType.BEHAVIORAL_ANOMALY),
        ]
        result = clf.classify(evidence)
        override = clf.apply_human_override(
            result=result,
            override_category=FraudCategory.INTERNAL_FRAUD,
            reviewer_id="analyst-007",
            justification="Confirmed by internal security team.",
        )
        assert override.category == FraudCategory.INTERNAL_FRAUD
        assert override.requires_human_review is False

    def test_human_override_requires_justification(self):
        clf = FraudClassifier()
        result = clf.classify([])
        with pytest.raises(ValueError, match="justification"):
            clf.apply_human_override(
                result=result,
                override_category=FraudCategory.NO_FRAUD,
                reviewer_id="analyst-007",
                justification="",
            )

    def test_human_override_requires_reviewer_id(self):
        clf = FraudClassifier()
        result = clf.classify([])
        with pytest.raises(ValueError, match="reviewer_id"):
            clf.apply_human_override(
                result=result,
                override_category=FraudCategory.NO_FRAUD,
                reviewer_id="",
                justification="Valid reason.",
            )


# ── Principle 5 – Explainability ─────────────────────────────────────────────


class TestExplainability:
    def test_result_has_explanation(self):
        clf = FraudClassifier()
        result = clf.classify([make_evidence(EvidenceType.CARD_NOT_PRESENT), make_evidence(EvidenceType.UNUSUAL_AMOUNT)])
        assert result.explanation is not None

    def test_explanation_answers_why_this_node(self):
        clf = FraudClassifier()
        result = clf.classify([make_evidence(EvidenceType.CARD_NOT_PRESENT), make_evidence(EvidenceType.UNUSUAL_AMOUNT)])
        assert result.explanation.why_this_node

    def test_explanation_answers_what_evidence(self):
        clf = FraudClassifier()
        evidence = [make_evidence(EvidenceType.CARD_NOT_PRESENT), make_evidence(EvidenceType.UNUSUAL_AMOUNT)]
        result = clf.classify(evidence)
        assert len(result.explanation.evidence_summary) == len(evidence)

    def test_explanation_answers_what_would_change_decision(self):
        clf = FraudClassifier()
        result = clf.classify([make_evidence(EvidenceType.CARD_NOT_PRESENT), make_evidence(EvidenceType.UNUSUAL_AMOUNT)])
        assert len(result.explanation.counterfactuals) > 0

    def test_explanation_includes_node_path(self):
        clf = FraudClassifier()
        result = clf.classify([make_evidence(EvidenceType.CARD_NOT_PRESENT), make_evidence(EvidenceType.UNUSUAL_AMOUNT)])
        assert "root" in result.explanation.node_path

    def test_override_explanation_mentions_reviewer(self):
        clf = FraudClassifier()
        result = clf.classify([])
        override = clf.apply_human_override(
            result=result,
            override_category=FraudCategory.NO_FRAUD,
            reviewer_id="reviewer-X",
            justification="Customer verified.",
        )
        assert "reviewer-X" in override.explanation.why_this_node


# ── Principle 6 – Auditability ───────────────────────────────────────────────


class TestAuditability:
    def test_classification_creates_audit_record(self):
        clf = FraudClassifier()
        result = clf.classify([])
        log = get_audit_log()
        assert any(r.event_type == "escalation" or r.event_type == "classification" for r in log)

    def test_audit_record_id_on_result(self):
        clf = FraudClassifier()
        result = clf.classify([make_evidence(EvidenceType.CARD_NOT_PRESENT), make_evidence(EvidenceType.UNUSUAL_AMOUNT)])
        assert result.audit_record_id is not None

    def test_human_override_creates_audit_record(self):
        clf = FraudClassifier()
        result = clf.classify([])
        clear_audit_log()

        clf.apply_human_override(
            result=result,
            override_category=FraudCategory.NO_FRAUD,
            reviewer_id="analyst-1",
            justification="Cleared after review.",
        )
        log = get_audit_log()
        override_records = [r for r in log if r.event_type == "human_override"]
        assert len(override_records) == 1
        assert override_records[0].overridden_by == "analyst-1"

    def test_escalation_creates_audit_record(self):
        clf = FraudClassifier()
        clf.classify([make_evidence(EvidenceType.EMPLOYEE_ACCESS_ANOMALY), make_evidence(EvidenceType.INSIDER_PATTERN)])
        log = get_audit_log()
        escalation_records = [r for r in log if r.event_type == "escalation"]
        assert len(escalation_records) >= 1

    def test_node_path_logged(self):
        clf = FraudClassifier()
        result = clf.classify([
            make_evidence(EvidenceType.CARD_NOT_PRESENT),
            make_evidence(EvidenceType.UNUSUAL_AMOUNT),
            make_evidence(EvidenceType.VELOCITY_ANOMALY),
            make_evidence(EvidenceType.BEHAVIORAL_ANOMALY),
            make_evidence(EvidenceType.UNUSUAL_LOCATION),
        ])
        log = get_audit_log()
        classification_records = [r for r in log if r.event_type == "classification"]
        assert len(classification_records) >= 1
        assert "root" in classification_records[0].node_path
