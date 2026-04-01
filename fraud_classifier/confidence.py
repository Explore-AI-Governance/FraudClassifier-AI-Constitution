"""
Confidence scoring and escalation module.

Enforces Governing Principle 3 – Confidence & Escalation:
  - High confidence   → classify
  - Medium confidence → flag for review
  - Low confidence    → human decision
"""

from __future__ import annotations

from dataclasses import dataclass

from .taxonomy import ConfidenceLevel, EvidenceType
from .evidence import Evidence


# ── Scoring weights ──────────────────────────────────────────────────────────
# Each evidence type contributes a base score toward confidence.
# The weights are intentionally transparent so that the impact of every
# signal can be explained (Principle 5 – Explainability).
EVIDENCE_WEIGHTS: dict[EvidenceType, float] = {
    EvidenceType.IDENTITY_MISMATCH: 0.30,
    EvidenceType.SYNTHETIC_IDENTITY_INDICATORS: 0.35,
    EvidenceType.DEVICE_FINGERPRINT_ANOMALY: 0.25,
    EvidenceType.BEHAVIORAL_ANOMALY: 0.20,
    EvidenceType.UNUSUAL_AMOUNT: 0.20,
    EvidenceType.UNUSUAL_LOCATION: 0.15,
    EvidenceType.VELOCITY_ANOMALY: 0.25,
    EvidenceType.CARD_NOT_PRESENT: 0.20,
    EvidenceType.CARD_PRESENT_ANOMALY: 0.25,
    EvidenceType.NEW_PAYEE: 0.15,
    EvidenceType.ACCOUNT_AGE_ANOMALY: 0.15,
    EvidenceType.DOCUMENT_FRAUD_INDICATORS: 0.35,
    EvidenceType.CREDIT_MISMATCH: 0.25,
    EvidenceType.EMPLOYEE_ACCESS_ANOMALY: 0.30,
    EvidenceType.INSIDER_PATTERN: 0.40,
}

# Thresholds that map a numeric score to a ConfidenceLevel tier.
HIGH_CONFIDENCE_THRESHOLD: float = 0.70
MEDIUM_CONFIDENCE_THRESHOLD: float = 0.40


@dataclass
class ConfidenceResult:
    """
    Outcome of the confidence calculation for a case.

    Attributes:
        score:            Numeric confidence in [0.0, 1.0].
        level:            Categorical tier derived from *score*.
        contributing_evidence: Evidence types that positively contributed.
    """

    score: float
    level: ConfidenceLevel
    contributing_evidence: list[EvidenceType]


def calculate_confidence(evidence_list: list[Evidence]) -> ConfidenceResult:
    """
    Derive a confidence score and tier from the supplied evidence.

    The score is the sum of weights for all recognised evidence types,
    capped at 1.0.  Every weight used in the calculation is recorded so
    the decision can always be explained.

    Parameters
    ----------
    evidence_list:
        Evidence items collected for the current case.

    Returns
    -------
    ConfidenceResult
    """
    total: float = 0.0
    contributors: list[EvidenceType] = []

    for item in evidence_list:
        weight = EVIDENCE_WEIGHTS.get(item.evidence_type, 0.0)
        if weight > 0.0:
            total += weight
            contributors.append(item.evidence_type)

    score = min(total, 1.0)

    if score >= HIGH_CONFIDENCE_THRESHOLD:
        level = ConfidenceLevel.HIGH
    elif score >= MEDIUM_CONFIDENCE_THRESHOLD:
        level = ConfidenceLevel.MEDIUM
    else:
        level = ConfidenceLevel.LOW

    return ConfidenceResult(
        score=round(score, 4),
        level=level,
        contributing_evidence=contributors,
    )


def should_escalate(confidence: ConfidenceResult) -> bool:
    """Return ``True`` when the case must be escalated to a human reviewer."""
    return confidence.level in (ConfidenceLevel.MEDIUM, ConfidenceLevel.LOW)
