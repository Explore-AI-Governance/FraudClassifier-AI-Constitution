"""
Evidence validation module.

Enforces Governing Principle 2 – Evidence First:
  "Every node requires defined evidence to proceed.  No evidence → no classification."
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .taxonomy import EvidenceType, NODE_REQUIRED_EVIDENCE


@dataclass
class Evidence:
    """
    Container for a single piece of evidence attached to a fraud case.

    Attributes:
        evidence_type: The canonical :class:`EvidenceType` signal.
        value:         The raw signal value (score, flag, description, etc.).
        source:        Where the evidence came from (system name, analyst ID …).
        metadata:      Optional free-form key/value pairs for additional context.
    """

    evidence_type: EvidenceType
    value: Any
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.evidence_type, EvidenceType):
            raise ValueError(
                f"evidence_type must be an EvidenceType member, got {self.evidence_type!r}"
            )
        if not self.source or not self.source.strip():
            raise ValueError("Evidence source must be a non-empty string.")


@dataclass
class EvidenceValidationResult:
    """Result returned by :func:`validate_evidence_for_node`."""

    is_valid: bool
    missing_evidence: list[EvidenceType]
    present_evidence: list[EvidenceType]


def validate_evidence_for_node(
    node: str,
    evidence_list: list[Evidence],
) -> EvidenceValidationResult:
    """
    Check whether *evidence_list* satisfies the requirements for *node*.

    Parameters
    ----------
    node:
        The decision-tree node name (must be a key of
        :data:`~fraud_classifier.taxonomy.NODE_REQUIRED_EVIDENCE`).
    evidence_list:
        Evidence items collected for the current case.

    Returns
    -------
    EvidenceValidationResult
        ``is_valid`` is ``True`` only when every required evidence type is present.
    """
    required = NODE_REQUIRED_EVIDENCE.get(node, [])
    present_types = {e.evidence_type for e in evidence_list}
    missing = [r for r in required if r not in present_types]
    present = [r for r in required if r in present_types]
    return EvidenceValidationResult(
        is_valid=len(missing) == 0,
        missing_evidence=missing,
        present_evidence=present,
    )
