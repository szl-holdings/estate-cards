# Fail-closed showcase writes across HF source-manifest boundaries

**Incident observed:** 2026-11-20 07:48–07:53 UTC.
**Source owner:** `szl-holdings/szl-khipu`.
**Affected Space:** `SZLHOLDINGS/khipu-proof-loom`.
**Writer to repair:** `szl-holdings/estate-cards`.

## Reproduced evidence, not a hypothetical style problem

The public HF Space at immutable revision
`67954832e01c335730a3b68c678e25f798a8ab9c` is
`RUNTIME_ERROR`. Its provider `runtime.errorMessage` explicitly includes
`RuntimeError: SOURCE_FILE_BYTES_MISMATCH` at startup in
`app.py:_source_identity()`. Public `SOURCE.json` claims canonical
`szl-khipu` source `c07648b71b7d0eb0a72bdbff6e98fb5e28eff0e8`
and lists **15** pinned source/data files.

An independently downloaded **15-of-15** source parity check found 14 exact
Hub bytes match their SOURCE.json and pinned GitHub versions. Only
`README.md` differs:

| Field | Pinned canonical GitHub | Live immutable Hub |
|---|---|---|
| Size | 6,255 bytes | 7,101 bytes |
| SHA-256 | `4a538b2149702bea705f70defae75f903a6d047aaf311f205150937d90e4abe3` | `394ee69c35c1257949246d71fd191e0f46e0fc08765851b424f920c78e5fa671` |

The exact diff adds only an `SZL estate showcase card` after the owner
README, including the marker `szl:showcase-card v1 generated
2026-11-20T06:25:18Z by szl-holdings/estate-cards weaver v0.1.0`.
This extra README content is sufficient to trip the intentional startup
integrity check. Do **not** disable the application's validation to fix it.

Host receipt (no private keys or raw credentials):
`C:\SZL\work\szl-convergence-20261120T0750Z\proofloom_manifest_audit.json`,
SHA-256 `016ab46bd7fd542033d219c9ca12034c58f1e683f7ef761eebab0537e7de3308`.

## This source-owned repair

`weaver/source_integrity.py` performs a bounded GET for
`SOURCE.json` at the fixed HF origin before any README commit.
If SOURCE.json exists, even under an unknown schema, the showcase writer
holds; it has **no authority to modify that README**. Any failed/malformed,
oversized, redirected, rate-limited or unauthorized read also holds.
Only an explicit HTTP 404 permits the existing README append path.

`weaver/rollout_hf.py:ndjson_commit` now invokes that guard
immediately before its provider mutation. It also reads the exact current
Hub HEAD and places that SHA in the documented Hugging Face NDJSON commit
header `parentCommit`; the provider rejects concurrent writer changes
rather than silently overwriting them. This is a compare-and-swap check,
not a new distributed lease. The writer also checks `SOURCE.json` a second
time and compares the latest observed README against the caller's original
README before allowing the commit. If the README was changed after card
generation, it is denied instead of silently overwriting an owner's edit.
The existing receipt/STOP mechanism remains.
`weaver/cards.py:fetch_readme` separately
stops treating every HTTP/network error as a missing README:
only an actual 404 means absent. Redirects, transient 5xx, 429,
401/403, corrupt UTF-8 or unexpected responses hold instead of composing
a new card over unknown existing content.

The upload operation attempts **one** parent-CAS-bound POST. A 429, 503,
timeout, connection loss or unknown provider outcome is a HOLD with a fixed
reason; it is **not retried** or logged with a raw provider response. Even a
successful HTTP 200 means provider acceptance, not source/runtime readback.
Independent Hub source and UI confirmation remains an owner release gate.

This is **fail-closed and source-only**. It does not remove generated
SVGs, delete existing Hub cards, modify Space privacy, grant model
training authority or republish the Space.

## Recovery sequence for the **separate** approved source owner

1. Merge and distribute the new weaver guard under normal protections.
   Stop/finish any already-running old weaver worker before restoring the
   source-owned Space, because source changes do not patch a live process.
2. On `szl-holdings/szl-khipu`, use the **existing**
   `.github/workflows/publish-proof-loom.yml` protected-main
   publisher, which is push-to-main and path-scoped (no workflow_dispatch).
   Its `scripts/publish_proofloom.py` stages 15 pinned files plus
   SOURCE.json, checks the parent Git revision, performs readback and
   validates the Gradio runtime. Do not upload one README directly or
   manually edit SOURCE.json outside that owner-owned publisher.
3. Verify exact byte parity for **all** managed files and provider
   `SOURCE.json` at the new immutable Hub revision. Require RUNNING and
   real `/config` source-marker, 3D components and API bindings; then run
   bounded browser smoke and negative/error tests. An HTTP 200 alone or
   `RUNNING` stage alone cannot establish UI/source acceptance.
4. If provider auth, rate limit, parent-CAS, Gradio runtime or private
   evidence gates refuse, preserve that HOLD and attach receipts. Do not
   retry using a different credential, bypass production check, or
   claim signed attestation from a SHA-256 checksum.

Reference: the protected `szl-khipu` project README states that Proof Loom
is a CPU-only public exact-math demo. It is **not** neural model training,
Lean kernel replay, or independently signed inference.
