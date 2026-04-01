"""
FraudClassifier decision-tree engine.

Enforces all six Governing Principles from the AI Constitution:
  1. Taxonomy Fidelity  – follow the decision tree exactly; no invented categories.
  2. Evidence First     – every node validates required evidence before proceeding.
  3. Confidence & Escalation – HIGH → classify; MEDIUM → review; LOW → human.
  4. Human-in-the-Loop – certain nodes always require human approval.
  5. Explainability     – every result carries a full :class:`Explanation`.
  6. Auditability       – every path, evidence set, and override is logged.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from .audit import AuditLogger
from .confidence import calculate_confidence, should_escalate, ConfidenceResult
from .evidence import Evidence, validate_evidence_for_node
from .explainer import Explanation, build_explanation
from .taxonomy import (
    ConfidenceLevel,
    FraudCategory,
    HUMAN_APPROVAL_REQUIRED_NODES,
)


# ── Result dataclass ─────────────────────────────────────────────────────────


@dataclass
class ClassificationResult:
    """
    The complete output of a :class:`FraudClassifier` run.

    Attributes:
        case_id:              Unique identifier for this case.
        category:             Final :class:`FraudCategory` outcome.
        confidence:           Confidence result (score + level + contributors).
        explanation:          Full :class:`Explanation` (why/evidence/counterfactuals).
        node_path:            Ordered list of decision-tree nodes traversed.
        requires_human_review: ``True`` when a human must approve/decide.
        human_approval_node:  Node name that triggered the human-approval requirement.
        audit_record_id:      UUID of the primary audit record for this result.
    """

    case_id: str
    category: FraudCategory
    confidence: ConfidenceResult
    explanation: Explanation
    node_path: list[str] = field(default_factory=list)
    requires_human_review: bool = False
    human_approval_node: str | None = None
    audit_record_id: str | None = None


# ── Classifier ───────────────────────────────────────────────────────────────


class FraudClassifier:
    """
    Core classifier that walks the FraudClassifier decision tree.

    Parameters
    ----------
    audit_logger:
        :class:`~fraud_classifier.audit.AuditLogger` instance.  One is created
        automatically if not supplied.
    """

    def __init__(self, audit_logger: AuditLogger | None = None) -> None:
        self._audit = audit_logger or AuditLogger()

    # ── Public API ────────────────────────────────────────────────────────────

    def classify(
        self,
        evidence_list: list[Evidence],
        case_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ClassificationResult:
        """
        Run the full classification decision tree on the supplied evidence.

        Parameters
        ----------
        evidence_list:
            All evidence items collected for the case.
        case_id:
            Optional caller-supplied identifier; a UUID is generated if omitted.
        metadata:
            Optional free-form metadata stored in the audit record.

        Returns
        -------
        ClassificationResult
        """
        case_id = case_id or str(uuid.uuid4())
        node_path: list[str] = ["root"]
        meta = metadata or {}

        # ── Principle 3: calculate confidence up front ───────────────────────
        confidence = calculate_confidence(evidence_list)
        evidence_type_names = [e.evidence_type.value for e in evidence_list]

        # ── Walk the decision tree ───────────────────────────────────────────
        category, final_node, requires_review, approval_node = self._walk_tree(
            case_id=case_id,
            evidence_list=evidence_list,
            confidence=confidence,
            node_path=node_path,
        )

        # ── Principle 5: build explanation ───────────────────────────────────
        explanation = build_explanation(
            node_path=node_path,
            final_node=final_node,
            category=category,
            evidence_list=evidence_list,
            confidence=confidence,
        )

        # ── Principle 6: emit audit record ───────────────────────────────────
        audit_record = self._audit.log_classification(
            case_id=case_id,
            node_path=node_path,
            category=category.value,
            confidence=confidence.score,
            evidence_types=evidence_type_names,
            notes=explanation.why_this_node,
            extra=meta,
        )

        return ClassificationResult(
            case_id=case_id,
            category=category,
            confidence=confidence,
            explanation=explanation,
            node_path=list(node_path),
            requires_human_review=requires_review,
            human_approval_node=approval_node,
            audit_record_id=audit_record.record_id,
        )

    def apply_human_override(
        self,
        result: ClassificationResult,
        override_category: FraudCategory,
        reviewer_id: str,
        justification: str,
    ) -> ClassificationResult:
        """
        Allow a human reviewer to override an AI recommendation.

        The override is logged with the reviewer identity and justification.
        The AI may recommend but never mandate irreversible actions (Principle 4).

        Parameters
        ----------
        result:
            Original :class:`ClassificationResult` to override.
        override_category:
            The human-assigned :class:`FraudCategory`.
        reviewer_id:
            Identity of the approving human reviewer.
        justification:
            Reason for the override (required).

        Returns
        -------
        ClassificationResult
            Updated result with the override applied and a new audit record.
        """
        if not justification or not justification.strip():
            raise ValueError("Human override requires a non-empty justification.")
        if not reviewer_id or not reviewer_id.strip():
            raise ValueError("Human override requires a non-empty reviewer_id.")

        audit_record = self._audit.log_human_override(
            case_id=result.case_id,
            node_path=result.node_path,
            original_category=result.category.value,
            override_category=override_category.value,
            overridden_by=reviewer_id,
            justification=justification,
        )

        # Rebuild explanation to reflect the override
        override_explanation = Explanation(
            why_this_node=(
                f"Human override by '{reviewer_id}': {justification}  "
                f"(Original AI recommendation: {result.category.value})"
            ),
            evidence_summary=result.explanation.evidence_summary,
            counterfactuals=[
                "This classification was set by a human reviewer and supersedes the AI recommendation."
            ],
            confidence_breakdown=result.explanation.confidence_breakdown,
            node_path=result.node_path,
        )

        return ClassificationResult(
            case_id=result.case_id,
            category=override_category,
            confidence=result.confidence,
            explanation=override_explanation,
            node_path=result.node_path,
            requires_human_review=False,
            human_approval_node=result.human_approval_node,
            audit_record_id=audit_record.record_id,
        )

    # ── Decision tree ─────────────────────────────────────────────────────────

    def _walk_tree(
        self,
        case_id: str,
        evidence_list: list[Evidence],
        confidence: ConfidenceResult,
        node_path: list[str],
    ) -> tuple[FraudCategory, str, bool, str | None]:
        """
        Traverse the decision tree and return
        ``(category, final_node, requires_review, approval_node)``.

        The tree is evaluated in priority order.  Each branch first validates
        evidence (Principle 2); if evidence is missing the branch is skipped and
        the ``INSUFFICIENT_EVIDENCE`` outcome is returned.
        """
        present = {e.evidence_type for e in evidence_list}

        # ── Principle 3: LOW confidence → human decision immediately ─────────
        if confidence.level == ConfidenceLevel.LOW:
            node_path.append("low_confidence_escalation")
            self._audit.log_escalation(
                case_id=case_id,
                node_path=node_path,
                reason="Confidence too low for automated classification.",
                confidence=confidence.score,
                evidence_types=[e.evidence_type.value for e in evidence_list],
            )
            return (
                FraudCategory.PENDING_HUMAN_REVIEW,
                "low_confidence_escalation",
                True,
                "low_confidence_escalation",
            )

        # ── Branch: internal fraud ────────────────────────────────────────────
        branch_result = self._try_node(
            case_id=case_id,
            node="internal_check",
            node_path=node_path,
            evidence_list=evidence_list,
            confidence=confidence,
            outcome=FraudCategory.INTERNAL_FRAUD,
        )
        if branch_result is not None:
            return branch_result

        # ── Branch: synthetic identity ────────────────────────────────────────
        branch_result = self._try_node(
            case_id=case_id,
            node="synthetic_identity_check",
            node_path=node_path,
            evidence_list=evidence_list,
            confidence=confidence,
            outcome=FraudCategory.SYNTHETIC_IDENTITY,
        )
        if branch_result is not None:
            return branch_result

        # ── Branch: account takeover ─────────────────────────────────────────
        branch_result = self._try_node(
            case_id=case_id,
            node="account_takeover_check",
            node_path=node_path,
            evidence_list=evidence_list,
            confidence=confidence,
            outcome=FraudCategory.ACCOUNT_TAKEOVER,
        )
        if branch_result is not None:
            return branch_result

        # ── Branch: first-party fraud ─────────────────────────────────────────
        branch_result = self._try_node(
            case_id=case_id,
            node="first_party_check",
            node_path=node_path,
            evidence_list=evidence_list,
            confidence=confidence,
            outcome=FraudCategory.FIRST_PARTY_FRAUD,
        )
        if branch_result is not None:
            return branch_result

        # ── Branch: third-party fraud ─────────────────────────────────────────
        branch_result = self._try_node(
            case_id=case_id,
            node="third_party_check",
            node_path=node_path,
            evidence_list=evidence_list,
            confidence=confidence,
            outcome=FraudCategory.THIRD_PARTY_FRAUD,
        )
        if branch_result is not None:
            return branch_result

        # ── Branch: card-not-present fraud ────────────────────────────────────
        branch_result = self._try_node(
            case_id=case_id,
            node="cnp_check",
            node_path=node_path,
            evidence_list=evidence_list,
            confidence=confidence,
            outcome=FraudCategory.CARD_NOT_PRESENT_FRAUD,
        )
        if branch_result is not None:
            return branch_result

        # ── Branch: card-present fraud ────────────────────────────────────────
        branch_result = self._try_node(
            case_id=case_id,
            node="card_present_check",
            node_path=node_path,
            evidence_list=evidence_list,
            confidence=confidence,
            outcome=FraudCategory.CARD_PRESENT_FRAUD,
        )
        if branch_result is not None:
            return branch_result

        # ── No fraudulent pattern matched → no fraud ──────────────────────────
        node_path.append("no_fraud_check")
        return (FraudCategory.NO_FRAUD, "no_fraud_check", False, None)

    def _try_node(
        self,
        case_id: str,
        node: str,
        node_path: list[str],
        evidence_list: list[Evidence],
        confidence: ConfidenceResult,
        outcome: FraudCategory,
    ) -> tuple[FraudCategory, str, bool, str | None] | None:
        """
        Attempt to evaluate a single decision-tree node.

        Returns a result tuple if the node fires, or ``None`` if evidence is
        missing (the caller should try the next branch).
        """
        validation = validate_evidence_for_node(node, evidence_list)

        if not validation.is_valid:
            # Missing evidence – skip this branch silently (no audit spam).
            return None

        # Evidence satisfied – record the node in the path.
        node_path.append(node)

        # ── Principle 4: human-approval-required nodes ───────────────────────
        requires_human = node in HUMAN_APPROVAL_REQUIRED_NODES
        if requires_human:
            self._audit.log_escalation(
                case_id=case_id,
                node_path=node_path,
                reason=f"Node '{node}' always requires human approval (AI Constitution Principle 4).",
                confidence=confidence.score,
                evidence_types=[e.evidence_type.value for e in evidence_list],
            )
            return (
                FraudCategory.PENDING_HUMAN_REVIEW,
                node,
                True,
                node,
            )

        # ── Principle 3: MEDIUM confidence → flag for review ─────────────────
        if should_escalate(confidence):
            self._audit.log_escalation(
                case_id=case_id,
                node_path=node_path,
                reason=(
                    f"Confidence {confidence.level.value} ({confidence.score:.4f}) "
                    "is below the high threshold; flagged for human review."
                ),
                confidence=confidence.score,
                evidence_types=[e.evidence_type.value for e in evidence_list],
            )
            return (
                FraudCategory.PENDING_HUMAN_REVIEW,
                node,
                True,
                node,
            )

        # ── HIGH confidence + no forced-review node → classify ───────────────
        return (outcome, node, False, None)
