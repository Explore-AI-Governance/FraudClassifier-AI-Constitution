"""
Tests for the fraud taxonomy module.

Validates Governing Principle 1 (Taxonomy Fidelity):
  - Categories, evidence types, and confidence levels match specification.
  - No categories may exist outside the canonical taxonomy.
"""

import pytest
from fraud_classifier.taxonomy import (
    FraudCategory,
    ConfidenceLevel,
    EvidenceType,
    NODE_REQUIRED_EVIDENCE,
    HUMAN_APPROVAL_REQUIRED_NODES,
)


class TestFraudCategory:
    def test_all_expected_categories_exist(self):
        names = {c.value for c in FraudCategory}
        expected = {
            "no_fraud",
            "account_takeover",
            "synthetic_identity",
            "card_not_present_fraud",
            "card_present_fraud",
            "first_party_fraud",
            "third_party_fraud",
            "internal_fraud",
            "insufficient_evidence",
            "pending_human_review",
        }
        assert expected.issubset(names), f"Missing categories: {expected - names}"

    def test_no_extra_categories(self):
        """Principle 1: no invented categories outside the taxonomy."""
        known = {
            "no_fraud",
            "account_takeover",
            "synthetic_identity",
            "card_not_present_fraud",
            "card_present_fraud",
            "first_party_fraud",
            "third_party_fraud",
            "internal_fraud",
            "insufficient_evidence",
            "pending_human_review",
        }
        actual = {c.value for c in FraudCategory}
        extra = actual - known
        assert not extra, f"Unexpected categories found: {extra}"

    def test_categories_are_strings(self):
        for cat in FraudCategory:
            assert isinstance(cat.value, str)


class TestConfidenceLevel:
    def test_all_tiers_exist(self):
        assert ConfidenceLevel.HIGH.value == "high"
        assert ConfidenceLevel.MEDIUM.value == "medium"
        assert ConfidenceLevel.LOW.value == "low"

    def test_exactly_three_tiers(self):
        assert len(list(ConfidenceLevel)) == 3


class TestEvidenceType:
    def test_minimum_evidence_types_exist(self):
        """All types referenced in NODE_REQUIRED_EVIDENCE must be EvidenceType members."""
        all_et = {et for et in EvidenceType}
        for node, required in NODE_REQUIRED_EVIDENCE.items():
            for et in required:
                assert et in all_et, f"{et} for node '{node}' is not a recognised EvidenceType"


class TestNodeRequiredEvidence:
    def test_root_has_no_requirements(self):
        assert NODE_REQUIRED_EVIDENCE["root"] == []

    def test_all_tree_nodes_are_present(self):
        expected_nodes = {
            "root",
            "identity_check",
            "synthetic_identity_check",
            "account_takeover_check",
            "transaction_check",
            "cnp_check",
            "card_present_check",
            "application_check",
            "first_party_check",
            "third_party_check",
            "internal_check",
        }
        missing = expected_nodes - set(NODE_REQUIRED_EVIDENCE.keys())
        assert not missing, f"Tree nodes missing from NODE_REQUIRED_EVIDENCE: {missing}"


class TestHumanApprovalNodes:
    def test_human_approval_nodes_are_frozenset(self):
        assert isinstance(HUMAN_APPROVAL_REQUIRED_NODES, frozenset)

    def test_human_approval_nodes_in_tree(self):
        for node in HUMAN_APPROVAL_REQUIRED_NODES:
            assert node in NODE_REQUIRED_EVIDENCE, (
                f"'{node}' is in HUMAN_APPROVAL_REQUIRED_NODES but not in the decision tree"
            )
