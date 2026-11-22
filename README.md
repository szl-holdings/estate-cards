# estate-cards

The SZL Holdings card weaver: a receipt-honest showcase system for the Hugging Face
organization ([SZLHOLDINGS](https://huggingface.co/SZLHOLDINGS), ~680 repos) and the GitHub
organization ([szl-holdings](https://github.com/szl-holdings), ~181 repos).

Every repo gets a cutting-edge, top-tech-company-grade card with real graphs - deterministic
SVG charts rendered from dated audit snapshots and mesh receipts, in the KANCHAY design
language. No invented history, no fake benchmarks.

## What is here

| Path | What it is |
|---|---|
| `weaver/charts.py` | Stdlib-only SVG primitives: line, donut, horizontal bar, sparkline. KANCHAY palette (space navy `#030F29`, coral `#DF735F`, teal `#168f89`, hatun gold `#cda64a`, silver linework). Deterministic: same data in, same bytes out. |
| `weaver/audit.py` | Fresh estate audit: HF census (models/datasets/Spaces incl. runtime stages), GitHub census, open-PR count, commit counts for top-20 updated repos, mesh receipt inventory. Every number labeled MEASURED/UNKNOWN with source + UTC capture. Writes `data/audit-latest.json`. |
| `weaver/cards.py` | Card renderers. Doctrine: NEVER delete existing README content. Curated READMEs get a clearly-marked appended showcase section; bare repos get a composed card. Every card carries the receipt footer with generated_at and card id. |
| `weaver/policy.py` | Repo -> canonical GitHub source mapping, first-wave priority list. |
| `weaver/rollout_hf.py` | DRY-RUN by default. Explicit `--apply` and `SZL_HF_CARD_PUBLISH_TOKEN` are required for model/dataset writes. **Space README writes are denied**: only each GitHub source owner may publish its sealed Space artifacts and manifest in the approved window. |
| `data/` | Audit snapshots (historical views, keep every one). |
| `queue.jsonl` | The rollout queue (kind, repo, purpose). |
| `rollout_receipts.jsonl` | Per-repo commit receipts. |

## Usage

```bash
python -m weaver.audit        # fresh census -> data/audit-latest.json
python -m weaver.rollout_hf   # DRY RUN: review queue decisions, no HF commits
# Owner-reviewed model/dataset publication ONLY, one exact approved repo:
#   SZL_HF_CARD_APPROVED_TARGET=model:SZLHOLDINGS/example-model
#   SZL_HF_CARD_PUBLISH_TOKEN is injected by the protected operator environment.
#   Export neither value to logs or a public workflow; do not use workstation token files.
# python -m weaver.rollout_hf --apply --repo SZLHOLDINGS/example-model
# A general --apply without --repo refuses all writes. Every new target needs
# its own separately reviewed rights/provenance and operator admission.

```

## Card contract (peer-reviewed)

Design reviewed 2026-11-20 by Kimi K3.1 Pro (design receipt sha256
`f3b83d39e587a5c52069bc51ec34b2d8a2be1d7e31dab6245314dde5975755ef`):

- Every number binds to a status label: MEASURED / REPORTED / MODELED / UNKNOWN, an
  `observed_at` UTC time, and a source. `generated_at` never substitutes for `observed_at`.
- Chart budget: 3 max per card. Omit unavailable charts rather than fill the slot.
- Platform download counts are never expanded into invented history.
- Failed and interrupted runs are retained on training charts, not hidden.
- Amateur cards maximize badges and decimals; these cards maximize hierarchy, whitespace,
  direct labels, explicit baselines, and reproducible queries.

## License

MIT for this repository's code. The SZL Holdings name, wordmark and brand colors are
trademarks of SZL Holdings.

## Incident and admission contract — 2026-11-20

**Root-cause readback, immutable Hub revision
`SZLHOLDINGS/khipu-proof-loom@67954832e01c335730a3b68c678e25f798a8ab9c`.**
Its source-owned `SOURCE.json` pins `README.md` to 6,255 bytes and SHA-256
`4a538b2149702bea705f70defae75f903a6d047aaf311f205150937d90e4abe3`
from `szl-khipu@c07648b71b7d0eb0a72bdbff6e98fb5e28eff0e8`. An
estate-cards showcase section added on 2026-11-20T06:25:18Z changed the Hub
README to 7,101 bytes with SHA-256
`394ee69c35c1257949246d71fd191e0f46e0fc08765851b424f920c78e5fa671`.
All **other 14** `SOURCE.json` files match the immutable Hub bytes. The app
fails closed at startup with `SOURCE_FILE_BYTES_MISMATCH`; the error must **not**
be bypassed by editing code or simply updating the expected hash to match an
unauthorized Hub change.

This repo's generic card weaver is *not* the approved publisher for any Space.
Its rollout now denies all direct Space README writes, even when `--apply` is
supplied. The canonical `szl-khipu` owner must decide whether to restore the
source-pinned README or import the showcase card into **reviewed GitHub source**,
regenerate all file manifests, and publish the complete exact-source bundle
through its single authorized HF workflow after required tests and approvals.
No repair is proven until the running Space, immutable revision, browser and
receipt readbacks agree. A same-size mutation still fails the SHA-256 check.

Model and dataset cards remain eligible only for explicit operator-reviewed
`--apply` with an injected `SZL_HF_CARD_PUBLISH_TOKEN`. A failed or unreadable
existing README must STOP, never become an automatically composed replacement.
The card now labels model weights and evaluation as NOT VERIFIED, not
automatically "trained," and refreshes one well-formed managed section without
accumulating duplicates; malformed cards fail closed. A queue entry, passing
HTTP response, general owner instruction or presence of a local token file is
not authorization. Model/dataset provenance, base-model and license rights,
metadata and unknown/unsigned training claims require their own per-repo review.
The code makes no protected-branch, Cloudflare, Space, or credential changes
and does not silently archive anything.
