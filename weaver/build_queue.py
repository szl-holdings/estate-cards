"""Build queue.jsonl from data/audit-latest.json: first wave (curated) then full public org."""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys
sys.path.insert(0, ROOT)
from weaver import policy

audit = json.load(open(os.path.join(ROOT, 'data', 'audit-latest.json'), encoding='utf-8'))

PURPOSES = {
    'SZLHOLDINGS/salad-khipu-scholar-v1': 'LoRA adapter of the khipu scholar lane: Salad-governed SFT on Qwen (mesh carries its DSSE-signed boot/state/complete receipts). Canonical source: szl-holdings/szl-khipu-scholar.',
    'SZLHOLDINGS/salad-flagship54-v2': 'Flagship 54 v2 candidate. Heldout battery v2.1 (2026-11-19, MEASURED): verdict HELD per pre-registered rule (broken control tripped zero rules -> battery inadmissible) - NOT promoted. Honest card: no capability claim.',
    'SZLHOLDINGS/salad-x402-frontier-v2': 'x402 frontier lane candidate (receipted runs in frontier-54-runs).',
    'SZLHOLDINGS/SZL-Khipu-Yachay-Nano': 'Yachay nano: small sovereign model lane of the khipu family.',
    'SZLHOLDINGS/frontier-54-doctrine-math-r1-candidate': 'Doctrine-math candidate from the frontier-54 lane; promotion is owner-gated.',
    'SZLHOLDINGS/khipu-scholar-runs': 'Receipt ledger of the estate training lanes: mesh/ holds DSSE-signed boot/state/crash/complete records with training step/loss evidence; peerlab/ holds the first two-frontier-model co-discovery session (The Khipu Fold, sha256-chained).',
    'SZLHOLDINGS/frontier-54-runs': 'Run receipts of the flagship54 frontier lane (answers, partials, summaries; quota-hardened writers).',
    'SZLHOLDINGS/proving-ground-54h-mesh': 'Proving-ground 54h mesh: park receipts and lane evidence for the proving-ground audit family.',
    'SZLHOLDINGS/khipu-scholars-sft-v1': 'SFT corpus of the khipu scholar lanes (frozen, corpus sha receipted in the training commands).',
    'SZLHOLDINGS/mesh-liveness': 'DSSE beacon heartbeats of the szl-mesh gossip layer (khipu/*-beacon.json per lane).',
    'SZLHOLDINGS/a11oy': 'A11oy: the governed-AI command center front door (deny-by-default, signed receipts). Source: szl-holdings/a11oy.',
    'SZLHOLDINGS/szl-command-lab': 'The searchable estate portfolio Space.',
    'SZLHOLDINGS/llm-router-live': 'Live mirror of the SZL Router inference flagship. Source: szl-holdings/szl-router.',
}

queue = []
for kind, repo in policy.FIRST_WAVE:
    if not policy.source_managed(kind, repo):
        queue.append({'kind': kind, 'repo': repo, 'purpose': PURPOSES.get(repo)})

# full org: everything public, models first, then datasets, then spaces
seen = set((k, r) for k, r in policy.FIRST_WAVE)
for kind, key in (('model', 'hf_models'), ('dataset', 'hf_datasets'), ('space', 'hf_spaces')):
    for item in audit[key]['items']:
        rid = item['id']
        if item.get('private') or policy.source_managed(kind, rid):
            continue
        if (kind, rid) in seen:
            continue
        queue.append({'kind': kind, 'repo': rid})
        seen.add((kind, rid))

private_note = []
for kind, key in (('model', 'hf_models'), ('dataset', 'hf_datasets'), ('space', 'hf_spaces')):
    for item in audit[key]['items']:
        if item.get('private'):
            private_note.append({'kind': kind, 'repo': item['id']})

with open(os.path.join(ROOT, 'queue.jsonl'), 'w', encoding='utf-8') as f:
    for q in queue:
        f.write(json.dumps(q, ensure_ascii=False) + chr(10))
with open(os.path.join(ROOT, 'data', 'private-at-audit.json'), 'w', encoding='utf-8') as f:
    json.dump(private_note, f, indent=1)
print('QUEUE_BUILT', len(queue), 'first_wave', len(policy.FIRST_WAVE), 'private_held', len(private_note))
print('PRIVATE:', json.dumps([p['repo'] for p in private_note]))
