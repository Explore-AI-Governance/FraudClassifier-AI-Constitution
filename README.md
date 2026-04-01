Date: 4/1/2026
# Explore AI Governance — FraudClassifier Constitution

**A lightweight, human-readable governance scaffold for applying the Federal Reserve’s FraudClassifier℠ model with AI — transparently, consistently, and with human oversight.** [1](https://fedpaymentsimprovement.org/strategic-initiatives/payments-security/fraudclassifier-model/)[2](https://www.federalreserve.gov/newsevents/pressreleases/other20200618a.htm)

This repository is intentionally simple: it’s a *conversation artifact*, not a product and not a reference implementation.

> **Big idea:** FraudClassifier gives the industry a shared fraud language.  
> This repo explores how AI can apply that language **with explicit governance-by-design**. [1](https://fedpaymentsimprovement.org/strategic-initiatives/payments-security/fraudclassifier-model/)[2](https://www.federalreserve.gov/newsevents/pressreleases/other20200618a.htm)

---

## 🌍 Why this exists

The Federal Reserve’s FraudClassifier℠ model was created to address inconsistent fraud classifications and definitions across the payments ecosystem. [1](https://fedpaymentsimprovement.org/strategic-initiatives/payments-security/fraudclassifier-model/)[2](https://www.federalreserve.gov/newsevents/pressreleases/other20200618a.htm)

FraudClassifier is designed to:
- classify fraud **independent of payment type, channel, or other payment characteristics** [1](https://fedpaymentsimprovement.org/strategic-initiatives/payments-security/fraudclassifier-model/)[2](https://www.federalreserve.gov/newsevents/pressreleases/other20200618a.htm)  
- use a **question-driven approach** starting with “who initiated the payment,” separating authorized vs. unauthorized initiation [1](https://fedpaymentsimprovement.org/strategic-initiatives/payments-security/fraudclassifier-model/)[2](https://www.federalreserve.gov/newsevents/pressreleases/other20200618a.htm)  
- include **supporting definitions** to promote consistent application across organizations [1](https://fedpaymentsimprovement.org/strategic-initiatives/payments-security/fraudclassifier-model/)[2](https://www.federalreserve.gov/newsevents/pressreleases/other20200618a.htm)  

That foundation is powerful. The question now is:

> **If AI helps classify fraud, how do we ensure it follows the same definitions, requires evidence, handles uncertainty responsibly, and stays auditable?** [1](https://fedpaymentsimprovement.org/strategic-initiatives/payments-security/fraudclassifier-model/)[2](https://www.federalreserve.gov/newsevents/pressreleases/other20200618a.htm)

---

## 📄 What is `constitution.md`?

A `constitution.md` is a **lightweight governance layer** written in plain language.

It defines how AI agents *should behave* when applying a decision tree like FraudClassifier:
- what evidence is required at each decision point  
- how confidence and uncertainty should be handled  
- when human review is mandatory  
- how decisions must be explainable and auditable  

It does **not**:
- replace the FraudClassifier model  
- create new fraud definitions  
- prescribe a specific vendor or architecture  

It simply makes governance explicit and reviewable. [1](https://fedpaymentsimprovement.org/strategic-initiatives/payments-security/fraudclassifier-model/)[2](https://www.federalreserve.gov/newsevents/pressreleases/other20200618a.htm)

- Start here: [`constitution.md`](./constitution.md)

---

## ✅ What’s in this repo

- **`constitution.md`** — the governance principles (human-readable)
- **`README.md`** — this landing page

That’s intentional: the goal is to keep it accessible for business, risk, policy, and SME audiences.

---

## 🤝 Who this is for

This repository is for:
- payments and fraud subject-matter experts  
- risk, compliance, audit, and governance leaders  
- policymakers exploring AI oversight  
- practitioners experimenting with tools like Claude or GitHub Copilot to reason through governed workflows  

No coding required to participate.

---

## ✍️ How to engage

- Read `constitution.md`
- Suggest principles / guardrails to strengthen governance
- Share scenarios where “authorized vs unauthorized” classification is difficult in practice
- Propose how evidence requirements and escalation should work

If you’re “vibe coding” with AI tools, this doc is meant to be something those tools can reason with — without turning this repo into a software project.

---

## 📌 Disclaimer

This repository is provided for exploratory and educational purposes only.  
Adoption is voluntary. Each organization remains responsible for its own governance, compliance, and operational decisions.

---

**Shared definitions create shared understanding.** [1](https://fedpaymentsimprovement.org/strategic-initiatives/payments-security/fraudclassifier-model/)[2](https://www.federalreserve.gov/newsevents/pressreleases/other20200618a.htm)  
**Explicit governance makes AI operationally trustworthy.**

