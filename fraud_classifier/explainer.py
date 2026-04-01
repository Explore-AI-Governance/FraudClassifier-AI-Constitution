"""
Explainability module.

Enforces Governing Principle 5 – Explainability:
  Every classification must answer:
    1. Why this node?
    2. What evidence?
    3. What would change the decision?
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .taxonomy import EvidenceType, FraudCategory, ConfidenceLevel, NODE_REQUIRED_EVIDENCE
from .evidence import Evidence
from .confidence import ConfidenceResult, EVIDENCE_WEIGHTS, HIGH_CONFIDENCE_THRESHOLD


@dataclass
class Explanation:
    """
    Human-readable explanation attached to every classification result.

    Attributes:
        why_this_node:        Narrative reason the decision tree reached this node.
        evidence_summary:     List of evidence items and their contribution weights.
        counterfactuals:      What evidence changes would alter the decision.
        confidence_breakdown: Numeric score and contributing evidence.
        node_path:            Ordered list of nodes traversed to reach the outcome.
    """

    why_this_node: str
    evidence_summary: list[dict]
    counterfactuals: list[str]
    confidence_breakdown: dict
    node_path: list[str] = field(default_factory=list)


def build_explanation(
    node_path: list[str],
    final_node: str,
    category: FraudCategory,
    evidence_list: list[Evidence],
    confidence: ConfidenceResult,
) -> Explanation:
    """
    Construct a full :class:`Explanation` for a classification decision.

    Parameters
    ----------
    node_path:
        Ordered list of decision-tree nodes traversed.
    final_node:
        The last node that produced the outcome.
    category:
        The :class:`FraudCategory` assigned (or process outcome).
    evidence_list:
        All evidence present on the case.
    confidence:
        Confidence result from :func:`~fraud_classifier.confidence.calculate_confidence`.

    Returns
    -------
    Explanation
    """
    # ── Why this node? ───────────────────────────────────────────────────────
    required = NODE_REQUIRED_EVIDENCE.get(final_node, [])
    present_types = {e.evidence_type for e in evidence_list}
    matched = [et for et in required if et in present_types]

    why_parts = [f"Decision-tree node '{final_node}' was reached via path: {' → '.join(node_path)}."]
    if matched:
        why_parts.append(
            f"Required evidence for this node was satisfied by: "
            f"{', '.join(et.value for et in matched)}."
        )
    why_parts.append(
        f"The resulting classification is '{category.value}' with "
        f"{confidence.level.value} confidence (score={confidence.score:.4f})."
    )
    why_this_node = " ".join(why_parts)

    # ── Evidence summary ─────────────────────────────────────────────────────
    evidence_summary = [
        {
            "type": e.evidence_type.value,
            "value": e.value,
            "source": e.source,
            "weight": EVIDENCE_WEIGHTS.get(e.evidence_type, 0.0),
        }
        for e in evidence_list
    ]

    # ── Counterfactuals ──────────────────────────────────────────────────────
    counterfactuals: list[str] = []

    if confidence.level == ConfidenceLevel.HIGH:
        counterfactuals.append(
            "Removing any high-weight evidence signal (weight ≥ 0.30) would "
            "likely reduce confidence below the high threshold and trigger review."
        )

    if confidence.level == ConfidenceLevel.MEDIUM:
        # How much more score is needed to reach high confidence?
        gap = HIGH_CONFIDENCE_THRESHOLD - confidence.score
        missing_signals = [
            et for et in EvidenceType if et not in present_types and EVIDENCE_WEIGHTS.get(et, 0.0) >= gap
        ]
        if missing_signals:
            counterfactuals.append(
                f"Adding any of the following evidence would raise confidence to HIGH and "
                f"allow direct classification: "
                f"{', '.join(et.value for et in missing_signals[:3])}."
            )
        counterfactuals.append(
            "Resolving contradictory evidence or obtaining additional corroborating "
            "signals would increase confidence and remove the review flag."
        )

    if confidence.level == ConfidenceLevel.LOW:
        counterfactuals.append(
            "Substantially more evidence is required before any automated "
            "classification can be issued.  A human investigator must decide."
        )

    if category == FraudCategory.INSUFFICIENT_EVIDENCE:
        missing_required = [et for et in required if et not in present_types]
        counterfactuals.append(
            f"Providing the following missing evidence would allow classification to proceed: "
            f"{', '.join(et.value for et in missing_required)}."
        )

    if not counterfactuals:
        counterfactuals.append("No simple counterfactual is available; multiple evidence changes would be required.")

    # ── Confidence breakdown ─────────────────────────────────────────────────
    confidence_breakdown = {
        "score": confidence.score,
        "level": confidence.level.value,
        "threshold_high": HIGH_CONFIDENCE_THRESHOLD,
        "contributing_evidence": [et.value for et in confidence.contributing_evidence],
    }

    return Explanation(
        why_this_node=why_this_node,
        evidence_summary=evidence_summary,
        counterfactuals=counterfactuals,
        confidence_breakdown=confidence_breakdown,
        node_path=node_path,
    )
