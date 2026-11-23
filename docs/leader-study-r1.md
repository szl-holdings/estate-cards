# estate-cards domain leader study r1 (propose-only)

Date: 2026-11-23. Method: web-verified leader landscape + governing-seat synthesis (Kimi nonce T3-ESTATE-CARDS-BRIEF). This card is documentation only; it changes no code, CI, config, or existing PR status. All absorb actions are FUTURE PROPOSALS (non-authorizing); implementation and merges remain separately reviewed and gated.

## Domain: receipt-honest model/dataset card generation and estate showcase charts

## Leaders studied (web-verified 2026-11-23)

1. Model Cards for Model Reporting (Mitchell et al., 2019) — https://arxiv.org/abs/1810.03993 — reference structure for intended use, out-of-scope use, and honest quantitative limitations; moat is the reporting discipline, not a claim that any estate model is validated.
2. Datasheets for Datasets (Gebru et al., 2018) — https://arxiv.org/abs/1803.09010 — per-dataset provenance, composition, consent, and retention documentation rows; moat is making dataset history and collection constraints explicit rather than implying provenance from a repository listing.
3. Hugging Face Model Cards documentation — https://huggingface.co/docs/hub/models-cards — Hub-native card metadata and section conventions readers expect; moat is interoperability with the target publishing surface, not evidence that a card's claims are true.
4. Observable Plot — https://github.com/observablehq/plot — concise declarative chart grammar producing deterministic SVG with sane scales and legends; moat is readable, reproducible visual encoding, not a measured speedup or a replacement for estate-cards' stdlib-only renderer.

## Absorb actions (FUTURE PROPOSALS, non-authorizing)

1. (Model Cards for Model Reporting) Propose a card-contract review mapping intended use, out-of-scope use, and quantitative limitations to explicit sections, with absent evidence rendered UNKNOWN rather than inferred. This would be a documentation/schema proposal only; it would not validate model behavior, create benchmarks, or authorize any Hub write.
2. (Datasheets for Datasets) Propose dataset-card rows for provenance, composition, consent, and retention, each carrying source and UTC capture consistent with data/audit-latest.json and MEASURED/UNKNOWN labeling. Missing consent or retention evidence must remain UNKNOWN; repository presence across the HF or GitHub estates is not proof of permission, quality, or completeness.
3. (Hugging Face Model Cards documentation) Propose a conformance checklist for Hub-native metadata and expected sections, checked in generated previews before any separately approved publication review. rollout_hf.py must remain DRY-RUN by default, and this proposal does not relax --apply, the single exact SZL_HF_CARD_APPROVED_TARGET, the protected SZL_HF_CARD_PUBLISH_TOKEN, or the DENIED state for Space README writes.
4. (Observable Plot) Propose a design-only comparison of its scale and legend conventions against the deterministic stdlib-only KANCHAY SVG charts, retaining byte-reproducible fixtures and explicit UNKNOWN handling for unaudited values. No dependency adoption, rendering change, performance improvement, or visual-parity claim is made; any benefit is unmeasured until a separately reviewed live run.
5. (baseline) Propose preserving fail-closed publication evidence by linking generated-card reviews to the audit receipt and the 2026-11-20 peer-review design receipt without treating peer review as proven trust. SOURCE_FILE_BYTES_MISMATCH must continue to fail closed after the 2026-11-20 loom incident; expected hashes must not be edited to bypass it, and third-party monitors and separate merge review remain required.

## Do not do (per governing seat)

Do not merge, bypass the signature wall, or claim implementation beyond this card.
