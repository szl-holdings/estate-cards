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
- The live endpoint pass preferred each Space's non-static READY domain. It observed 73 root responses at HTTP 200 and 52 `/healthz` responses at HTTP 200. Three Spaces had no READY domain.

The corrected live pass found four genuine root failures on the preferred non-static domains. Static alias hosts that returned 404 were excluded from this failure count. The affected IDs are

```text
SZLHOLDINGS/anatomy
SZLHOLDINGS/immune
SZLHOLDINGS/immune-lattice
SZLHOLDINGS/szl-constellation-staging
```

`SZLHOLDINGS/david-leads` served its root but timed out on `/healthz`. Several static nginx-style Spaces served their root while lacking `/healthz`, which is expected for that deployment shape and remains outside the strict Python service contract.

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

