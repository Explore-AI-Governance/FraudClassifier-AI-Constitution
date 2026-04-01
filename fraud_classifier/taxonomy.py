"""
Fraud taxonomy definitions.

Defines the canonical fraud categories, evidence types, and confidence levels
used throughout the FraudClassifier decision tree.  No category or shortcut
may be invented outside this module (Governing Principle 1 – Taxonomy Fidelity).
"""

from enum import Enum


class FraudCategory(str, Enum):
    """Canonical fraud classification outcomes."""

    # ── Leaf outcomes ────────────────────────────────────────────────────────
    NO_FRAUD = "no_fraud"
    ACCOUNT_TAKEOVER = "account_takeover"
    SYNTHETIC_IDENTITY = "synthetic_identity"
    CARD_NOT_PRESENT_FRAUD = "card_not_present_fraud"
    CARD_PRESENT_FRAUD = "card_present_fraud"
    FIRST_PARTY_FRAUD = "first_party_fraud"
    THIRD_PARTY_FRAUD = "third_party_fraud"
    INTERNAL_FRAUD = "internal_fraud"

    # ── Process outcomes ─────────────────────────────────────────────────────
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    PENDING_HUMAN_REVIEW = "pending_human_review"


class ConfidenceLevel(str, Enum):
    """Confidence tiers that govern the escalation path."""

    HIGH = "high"      # → classify directly
    MEDIUM = "medium"  # → flag for human review
    LOW = "low"        # → human decision required


class EvidenceType(str, Enum):
    """All recognised evidence signals accepted by the classifier."""

    # Identity signals
    IDENTITY_MISMATCH = "identity_mismatch"
    SYNTHETIC_IDENTITY_INDICATORS = "synthetic_identity_indicators"

    # Device / session signals
    DEVICE_FINGERPRINT_ANOMALY = "device_fingerprint_anomaly"
    BEHAVIORAL_ANOMALY = "behavioral_anomaly"

    # Transaction signals
    UNUSUAL_AMOUNT = "unusual_amount"
    UNUSUAL_LOCATION = "unusual_location"
    VELOCITY_ANOMALY = "velocity_anomaly"
    CARD_NOT_PRESENT = "card_not_present"
    CARD_PRESENT_ANOMALY = "card_present_anomaly"

    # Account / application signals
    NEW_PAYEE = "new_payee"
    ACCOUNT_AGE_ANOMALY = "account_age_anomaly"
    DOCUMENT_FRAUD_INDICATORS = "document_fraud_indicators"
    CREDIT_MISMATCH = "credit_mismatch"

    # Internal signals
    EMPLOYEE_ACCESS_ANOMALY = "employee_access_anomaly"
    INSIDER_PATTERN = "insider_pattern"


# ── Node-level evidence requirements ────────────────────────────────────────
# Maps every decision-tree node name to the minimum set of evidence types
# that must be present before the node can be evaluated (Principle 2).
NODE_REQUIRED_EVIDENCE: dict[str, list[EvidenceType]] = {
    "root": [],  # entry point – no evidence required to start
    "identity_check": [EvidenceType.IDENTITY_MISMATCH],
    "synthetic_identity_check": [
        EvidenceType.SYNTHETIC_IDENTITY_INDICATORS,
        EvidenceType.IDENTITY_MISMATCH,
    ],
    "account_takeover_check": [
        EvidenceType.IDENTITY_MISMATCH,
        EvidenceType.DEVICE_FINGERPRINT_ANOMALY,
    ],
    "transaction_check": [EvidenceType.UNUSUAL_AMOUNT],
    "cnp_check": [EvidenceType.CARD_NOT_PRESENT, EvidenceType.UNUSUAL_AMOUNT],
    "card_present_check": [EvidenceType.CARD_PRESENT_ANOMALY],
    "application_check": [EvidenceType.DOCUMENT_FRAUD_INDICATORS],
    "first_party_check": [
        EvidenceType.DOCUMENT_FRAUD_INDICATORS,
        EvidenceType.CREDIT_MISMATCH,
    ],
    "third_party_check": [
        EvidenceType.DOCUMENT_FRAUD_INDICATORS,
        EvidenceType.IDENTITY_MISMATCH,
    ],
    "internal_check": [
        EvidenceType.EMPLOYEE_ACCESS_ANOMALY,
        EvidenceType.INSIDER_PATTERN,
    ],
}

# Nodes that ALWAYS require human approval before a final classification is
# issued, regardless of confidence level (Principle 4).
HUMAN_APPROVAL_REQUIRED_NODES: frozenset[str] = frozenset(
    {
        "internal_check",
        "synthetic_identity_check",
        "first_party_check",
    }
)
