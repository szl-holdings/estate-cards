# Hugging Face Spaces audit and consolidation record

Captured 2026-11-26 from the SZLHOLDINGS organization with Desktop Commander.

## Inventory

The audit measured 80 Spaces.

- 78 runtimes reported RUNNING and 2 reported SLEEPING.
- 77 Spaces exposed a READY custom or Hub domain.
- 79 Spaces linked to at least one GitHub source URL.
- 33 Spaces were Python-only candidates by file topology.
- 69 Spaces mixed Python with web assets or JavaScript.
- 20 Spaces had no Python files.
- 68 READMEs mentioned Python, 58 mentioned a backend, 56 mentioned a frontend, and 75 mentioned consolidation. These README signals are advisory.
- The live endpoint pass probed the first READY domain for every Space. It observed 60 root responses at HTTP 200, 51 `/healthz` responses at HTTP 200, and 28 `/readyz` responses at HTTP 200.

The live pass recorded 29 Spaces with a root or health check failure or timeout. The affected IDs are

```text
SZLHOLDINGS/README
SZLHOLDINGS/anatomy
SZLHOLDINGS/david-leads
SZLHOLDINGS/foundation-confirmation-v2
SZLHOLDINGS/frontier-console
SZLHOLDINGS/governed-receipt-verifier
SZLHOLDINGS/immune
SZLHOLDINGS/immune-lattice
SZLHOLDINGS/khipu-hologram
SZLHOLDINGS/khipu-playground
SZLHOLDINGS/khipu-yachay
SZLHOLDINGS/prove-it
SZLHOLDINGS/szl-bench-suite
SZLHOLDINGS/szl-brand-campaign
SZLHOLDINGS/szl-command-center
SZLHOLDINGS/szl-constellation-staging
SZLHOLDINGS/szl-cram-demo
SZLHOLDINGS/szl-energy-ledger
SZLHOLDINGS/szl-forge-lab
SZLHOLDINGS/szl-frontier-deck
SZLHOLDINGS/szl-marketing
SZLHOLDINGS/szl-provenance-pitch
SZLHOLDINGS/szl-receipt-constellation
SZLHOLDINGS/szl-receipts-chain
SZLHOLDINGS/szl-safe-stack
SZLHOLDINGS/szl-second-brain
SZLHOLDINGS/szlholdings-si
SZLHOLDINGS/training-ledger-explorer
SZLHOLDINGS/wink-observatory
```

The two sleeping runtimes are `SZLHOLDINGS/immune-lattice` and `SZLHOLDINGS/szl-chief-engineer`. The three Spaces without a READY domain are `README`, `szl-brand-campaign`, and `szl-safe-stack`. `SZLHOLDINGS/szl-receipt-constellation` has no GitHub source URL.

## Safe consolidation

The strongest consolidation candidate is a three-Space family that shares the same Python FastAPI shell and the same source repository.

- `SZLHOLDINGS/frontier-showcase` is the canonical route host.
- `SZLHOLDINGS/measured-honesty-census` becomes the `/census` route.
- `SZLHOLDINGS/szl-energy-hologram` becomes the `/energy` route.
- All three currently share the same `app.py` bytes, Dockerfile, assets, and style files.
- All three read the `SZLHOLDINGS/frontier-54-runs` dataset. The showcase also reads `formula-proving-ground`.
- The existing browser code fetches Hugging Face data directly. The consolidated backend must own dataset retrieval, validation, timeout handling, and honest error receipts.
- The frontend must be server-rendered by Python templates or an equivalent Python-owned renderer. The current JavaScript-driven pages do not satisfy a strict pure-Python frontend requirement.

This change is source-owned. The Spaces must keep their existing domains until a reviewed redirect and receipt migration has passed.

## Required gates

The source owner must publish one sealed bundle through the approved workflow after

1. the Python application exposes the canonical, census, and energy routes;
2. dataset reads are server-side and bounded;
3. frontend and backend tests pass in hosted CI;
4. the exact GitHub revision is recorded in the Space manifest;
5. root, health, route, and error responses are verified live;
6. existing source, domains, and receipts are preserved;
7. redirects are reviewed and a migration tombstone is published;
8. no unique dataset, secret, or user artifact is stranded.

The estate-cards policy denies direct Space README writes. This record therefore does not mutate or delete any Space. It gives the source owner the exact consolidation boundary and verification gates.

## Other high-priority repairs

- `SZLHOLDINGS/frontier-console` serves its root but lacks `/healthz`.
- `SZLHOLDINGS/training-ledger-explorer` has no working root or health route despite a Python candidate topology.
- `SZLHOLDINGS/szlholdings-si` timed out on root and health checks.
- `SZLHOLDINGS/immune` and `SZLHOLDINGS/immune-lattice` need route-level checks against their documented NEXUS and Python channel contracts. Their GitHub documentation explicitly keeps both URLs until parity, restart persistence, and tombstone gates pass.
- Static or no-Python Spaces require separate source-owned migrations before they can meet the strict Python frontend and backend requirement.

