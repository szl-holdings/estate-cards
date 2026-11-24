# Leader Study - estate-cards - 2026-11-23 (W27 loop, propose-only)

Goal: study the current leaders in model-card transparency and AI supply-chain provenance,
then measure where estate-cards stands and what to absorb next. Propose-only per estate
doctrine: no merge without owner approval.

## Leaders studied

1. **A Large-Scale Measurement of AI Bill of Materials Completeness in Hugging Face Models**
   (arXiv 2607.17242, 2026-07). Empirical study of ~97.5K generated AIBOM artifacts across
   public HF model repositories. Key finding: AIBOM structure is complete but AI-specific
   documentation (datasets, limitations, safety-risk, environmental info) coverage is
   limited and varies by task/license/paper-reference characteristics.
2. **AI Transparency Atlas: Framework, Scoring, and Real-Time Model Card Evaluation
   Pipeline** (arXiv 2512.12443, 2025-12). Analyzed 5 frontier models + 100 HF model cards;
   found 947 unique section names; usage info appeared under 97 distinct labels. Built a
   weighted framework (8 sections, 23 subsections; Safety Evaluation 25%, Critical Risk 20%)
   benchmarked against EU AI Act Annex IV and the Stanford Transparency Index, with a
   cheap automated scoring pipeline (< 3 USD for 50 models).
3. **Position: Current Model Cards Are Insufficient for Downstream Governance of
   Open-Weight Foundation Models** (arXiv 2608.18086, 2026-08). Argues current cards fail
   downstream users who need to verify claims, evidence, and version-level changes.

## Where estate-cards already aligns or leads

- Source-sealed Spaces with writer admission gates and publisher tokens (merged #4/#9):
  upstream of the upstream-of-leaders problem: most HF repos cannot prove WHO wrote a card.
- Receipt-showcase doctrine: every card ships with measured receipts, matching the AIBOM
  gap (models lack machine-readable evidence, not structure).
- CAS parent pinning in rollouts (ndjson_commit parent_commit contract, #9): gives the
  version-level anchoring that 2608.18086 says downstream governance lacks.
- Provenance-chain fields landing estate-wide in receipt spec (W26L G3 merge, 2026-11-23).

## Absorb plan (propose-only, ranked)

1. **Card AIBOM completeness scorer (highest value).** Add tools/card_aibom_score.py that
   scores our card files against a fixed field set (license, datasets, limitations,
   safety-risk, environmental) and emits a receipt. Direct application of 2607.17242's
   evaluation axes to our own estate, zero new dependencies.
2. **Stable section vocabulary.** Adopt fixed section names for estate cards (single
   canonical schema instead of per-space naming), per the 947-section fragmentation finding
   in 2512.12443.
3. **Weighted transparency receipt.** Extend the scorer with the weighted rubric shape
   (safety-critical disclosures weighted above usage notes) so estate cards report one
   comparable number that auditors can trust.
4. **Downstream verification hooks.** Document how a third party verifies a card's claims
   from receipts + CAS parent pins alone (no trust in us), answering 2608.18086 directly.

## Non-goals

No Space secrets, tokens, CI, or release changes in this PR. Text-only leader study.

## Requested review

Owner + council. This PR is documentation; it proposes the absorb plan for a follow-up
implementation PR.
