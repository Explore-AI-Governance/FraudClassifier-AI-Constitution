"""
FraudClassifier – public package API.

Import shortcuts so callers can write::

    from fraud_classifier import FraudClassifier, Evidence, FraudCategory
"""

from .audit import AuditLogger, AuditRecord, get_audit_log, clear_audit_log
from .classifier import ClassificationResult, FraudClassifier
from .confidence import ConfidenceResult, calculate_confidence
from .evidence import Evidence, EvidenceValidationResult, validate_evidence_for_node
from .explainer import Explanation, build_explanation
from .taxonomy import (
    ConfidenceLevel,
    EvidenceType,
    FraudCategory,
    HUMAN_APPROVAL_REQUIRED_NODES,
    NODE_REQUIRED_EVIDENCE,
)

__all__ = [
    # Core classifier
    "FraudClassifier",
    "ClassificationResult",
    # Evidence
    "Evidence",
    "EvidenceValidationResult",
    "validate_evidence_for_node",
    # Confidence
    "ConfidenceResult",
    "calculate_confidence",
    # Explainability
    "Explanation",
    "build_explanation",
    # Audit
    "AuditLogger",
    "AuditRecord",
    "get_audit_log",
    "clear_audit_log",
    # Taxonomy
    "FraudCategory",
    "EvidenceType",
    "ConfidenceLevel",
    "HUMAN_APPROVAL_REQUIRED_NODES",
    "NODE_REQUIRED_EVIDENCE",
]
