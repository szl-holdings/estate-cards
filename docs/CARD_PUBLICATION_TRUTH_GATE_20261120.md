# HF card truth and read-preflight gate — 2026-11-20

Status: **SOURCE-ONLY PATCH**. Does not change any Hugging Face model, Space,
dataset, credential, visibility, signed receipt or runtime. The separate
`estate-cards` source-owner / immutable-manifest / parent-CAS protection is
already proposed in draft PR #3. That protection is **still required**.

## Incident evidence (read-only public)

The public `SZLHOLDINGS/khipu-proof-loom` Space at revision
`67954832e01c335730a3b68c678e25f798a8ab9c` reported `RUNTIME_ERROR`.
Its `SOURCE.json` pinned the canonical `szl-holdings/szl-khipu` source
revision `c07648b71b7d0eb0a72bdbff6e98fb5e28eff0e8`. A scoped anonymous
readback found that `README.md` differed from the pin: expected 6,255 bytes
(SHA-256 prefix `4a538b2149702bea`), observed 7,101 bytes (prefix
`394ee69c35c12579`). The other six sampled source/data files matched.
The last Space commit was an estate-card append. This is strong evidence of a
source-sealing conflict, not a proof of a malicious actor.

**Do not loosen `_source_identity()` in the Khipu owner application.**
Owner-governed recovery must restore an immutable reviewed source revision
and validate all 15 declared artifacts and actual 3D/frontend API behavior.
The generic card weaver must stop modifying source-sealed files; see draft
PR #3. A no-README HTTP 404 is not an exception to that separate rule.

## Independent failure mode closed here

The source's previous `weaver/cards.py::fetch_readme` swallowed **all**
transport/auth/quota errors and returned `None`. The card renderer interprets
`None` as an absent README and may compose an entirely new one. A temporary
HTTP 429, HTTP 403, interrupted connection or an HTML challenge could thus
authorize accidental replacement of curator-owned source content.

It now returns `None` **only** for a genuine HTTP 404. All other source
failures HOLD before the write path. The read is capped at 1 MiB, accepts
text/plain or markdown-like media types, validates UTF-8, refuses redirect
requests that could propagate an Authorization header, and does not inherit
ambient network proxy settings. Secret reading happens only at the actual
authorized fetch, not when the pure card-rendering module is imported. These
are defense-in-depth source checks; an authenticated provider control-plane
readback and owner-approved CAS are separate gates.

## Training and rights claims

Anonymous Hugging Face inventory on 2026-11-20 observed 401 visible model
namespace repositories, 172 datasets and 78 Spaces (76 RUNNING, one PAUSED,
one RUNTIME_ERROR). Model names, a successful Hub upload, `pipeline_tag`,
card artwork, and generic source-link badges are **not** evidence of trained
weights, held-out evaluation, license clearance, checkpoint completeness or
model readiness. The inventory's zero listing-level `license:` tags does
**not** prove license absence or waive file-level review.

The previous card text described every model namespace as a "trained artifact
in the governed factory." The patched renderer instead states **UNKNOWN**
training/evaluation and **NOT_REVIEWED** rights/weights. Optional source
metadata is restricted to narrowly declared descriptive fields and clearly
labeled unverified; it cannot inject arbitrary markup or assert `SIGNED` /
`TRAINED` via arbitrary status keys. Dataset purposes are HTML-escaped and
explicitly caller-declared, not signed source-lineage evidence.

### Protected acceptance

```
python -B -m unittest discover -s tests -p 'test_*.py' -v
```

Run the pinned two-version CI workflow, review every adverse test, then
request an independent non-author reviewer. This patch does **not** deploy
cards or recover the already-failed Space, and it creates no training run,
no model/card revenue claim, no Cloudflare settings change, no credential
rotation and no publication authority.

The corrective design follows source-owner boundaries and OTel-style explicit
status semantics rather than uniform cosmetic "green" cards. Study
Hugging Face's [model cards](https://huggingface.co/docs/hub/model-cards),
[SLSA provenance](https://slsa.dev/spec/v1.2/build-provenance),
[OpenSSF Scorecard](https://scorecard.dev/), and the original Khipu
source owner's [publish contract](https://github.com/szl-holdings/szl-khipu/blob/main/scripts/publish_proofloom.py).
