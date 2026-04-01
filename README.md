# FraudClassifier AI Constitution

Ensure FraudClassifier decisions are consistent, explainable, evidence-based,
and aligned with industry definitions.

---

## Governing Principles

| # | Principle | Implementation |
|---|-----------|---------------|
| 1 | **Taxonomy Fidelity** | `fraud_classifier/taxonomy.py` – canonical `FraudCategory`, `EvidenceType`, and `ConfidenceLevel` enums; no category may be invented outside them. |
| 2 | **Evidence First** | `fraud_classifier/evidence.py` – every decision-tree node declares required evidence; classification is blocked when evidence is missing. |
| 3 | **Confidence & Escalation** | `fraud_classifier/confidence.py` – scores evidence; HIGH (≥ 0.70) → classify, MEDIUM (≥ 0.40) → flag for review, LOW → human decision. |
| 4 | **Human-in-the-Loop** | `fraud_classifier/classifier.py` – certain nodes (`internal_check`, `synthetic_identity_check`, `first_party_check`) always require human approval; AI may recommend, never mandate irreversible actions. |
| 5 | **Explainability** | `fraud_classifier/explainer.py` – every result carries *why this node*, *what evidence*, and *what would change the decision*. |
| 6 | **Auditability** | `fraud_classifier/audit.py` – all paths, evidence, escalations, and human overrides are written to an append-only audit log. |

---

## Quick Start

```python
from fraud_classifier import FraudClassifier, Evidence, EvidenceType, FraudCategory

clf = FraudClassifier()

evidence = [
    Evidence(evidence_type=EvidenceType.CARD_NOT_PRESENT,   value=True,    source="payment_gateway"),
    Evidence(evidence_type=EvidenceType.UNUSUAL_AMOUNT,     value=9500.00, source="transaction_monitor"),
    Evidence(evidence_type=EvidenceType.VELOCITY_ANOMALY,   value=True,    source="rule_engine"),
    Evidence(evidence_type=EvidenceType.BEHAVIORAL_ANOMALY, value=True,    source="ml_model"),
    Evidence(evidence_type=EvidenceType.UNUSUAL_LOCATION,   value=True,    source="geo_service"),
]

result = clf.classify(evidence, case_id="TXN-20240401-001")

print(result.category)               # FraudCategory.CARD_NOT_PRESENT_FRAUD
print(result.confidence.level)       # ConfidenceLevel.HIGH
print(result.requires_human_review)  # False

# Full explainability
print(result.explanation.why_this_node)
print(result.explanation.counterfactuals)

# Human override (Principle 4)
override = clf.apply_human_override(
    result=result,
    override_category=FraudCategory.NO_FRAUD,
    reviewer_id="analyst-007",
    justification="Customer confirmed legitimate travel purchase.",
)
print(override.category)  # FraudCategory.NO_FRAUD
```

---

## Package Structure

```
fraud_classifier/
├── __init__.py       – Public API
├── taxonomy.py       – Canonical enums and node requirements   (Principle 1)
├── evidence.py       – Evidence dataclass and node validation  (Principle 2)
├── confidence.py     – Scoring weights and escalation logic    (Principle 3)
├── classifier.py     – Decision-tree engine + human override   (Principles 1–6)
├── explainer.py      – Why/evidence/counterfactual generator   (Principle 5)
└── audit.py          – Append-only audit logger                (Principle 6)

tests/
├── test_taxonomy.py
├── test_evidence.py
├── test_confidence.py
├── test_explainer.py
├── test_audit.py
└── test_classifier.py   (integration – all six principles)
```

---

## Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```
