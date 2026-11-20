"""Org-level graphs for the GitHub profile README: honest, from audit-latest only."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from weaver import charts

audit = json.load(open(os.path.join(ROOT, 'data', 'audit-latest.json'), encoding='utf-8'))
OUT = os.path.join(ROOT, 'assets')
os.makedirs(OUT, exist_ok=True)
ts = audit['generated_at']

# 1) fleet census donut
fleet = [('GitHub repos', audit['gh']['total'], '#5C6B86'),
         ('HF models', audit['hf_models']['total'], '#DF735F'),
         ('HF datasets', audit['hf_datasets']['total'], '#168f89'),
         ('HF Spaces', audit['hf_spaces']['total'], '#cda64a')]
open(os.path.join(OUT, 'org-fleet.svg'), 'w', encoding='utf-8').write(
    charts.donut(fleet, title='Estate artifacts (MEASURED %s)' % ts))

# 2) commit activity top-10 measured subset
gc = audit.get('gh_commits') or {}
detail = gc.get('detail') or {}
if detail:
    top = sorted(detail.items(), key=lambda kv: -kv[1])[:10]
    open(os.path.join(OUT, 'org-commits.svg'), 'w', encoding='utf-8').write(
        charts.hbar([(k, v) for k, v in top], title='Commits - measured top-20 most-updated repos (%s)' % ts))

# 3) Space runtime stages donut
sr = (audit.get('space_runtime') or {}).get('stages') or {}
if sr:
    counts = {}
    for stage in sr.values():
        stage = 'RUNNING' if stage == 'RUNNING' else str(stage).split(':')[0]
        counts[stage] = counts.get(stage, 0) + 1
    pal = {'RUNNING': '#168f89', 'BUILDING': '#cda64a', 'NO_APP_FILE': '#5C6B86', 'PAUSED': '#9AA7BD', 'ERR': '#c0392b'}
    parts = [(k, counts[k], pal.get(k, '#9AA7BD')) for k in sorted(counts)]
    open(os.path.join(OUT, 'org-spaces.svg'), 'w', encoding='utf-8').write(
        charts.donut(parts, title='Space runtime stages (MEASURED %s)' % ts))

# 4) receipt families on khipu-scholar-runs mesh
mesh = audit.get('mesh') or {}
files = mesh.get('files') or []
if files:
    fam = {}
    for f in files:
        import os as _os
        base = _os.path.basename(f)
        key = base.split('-20')[0]
        fam[key] = fam.get(key, 0) + 1
    top = sorted(fam.items(), key=lambda kv: -kv[1])[:12]
    open(os.path.join(OUT, 'org-mesh.svg'), 'w', encoding='utf-8').write(
        charts.hbar([(k, v) for k, v in top], title='Mesh receipt families, khipu-scholar-runs (MEASURED %s)' % ts))

print('ORG_GRAPHS_DONE', sorted(os.listdir(OUT)))
