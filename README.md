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
| `weaver/rollout_hf.py` | Paced HF roller: queue-driven (14s+ commit spacing under the measured ~320/h org quota), 429 exponential backoff, one receipt line per repo, resumable, STOP-file halt. |
| `data/` | Audit snapshots (historical views, keep every one). |
| `queue.jsonl` | The rollout queue (kind, repo, purpose). |
| `rollout_receipts.jsonl` | Per-repo commit receipts. |

## Usage

```bash
python -m weaver.audit        # fresh census -> data/audit-latest.json
python -m weaver.rollout_hf   # process queue.jsonl at a safe pace
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
