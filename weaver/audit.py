"""estate audit: fresh, receipt-labeled census of GitHub org + HF org + mesh evidence.

Every number is labeled MEASURED with source + UTC. Output: data/audit-<ts>.json
"""
import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error
import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from weaver import charts  # smoke-test import

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN = open('C:/Users/steph/.cache/huggingface/token', encoding='utf-8').read().strip()
H = {'Authorization': 'Bearer ' + TOKEN}
ORG = 'SZLHOLDINGS'
GH_ORG = 'szl-holdings'


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def get(url, timeout=60):
    req = urllib.request.Request(url, headers=H)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def gh(args, timeout=120):
    r = subprocess.run(['gh'] + args, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError('gh failed: ' + (r.stderr or '')[:200])
    return r.stdout


def hf_census(kind):
    ep = {'models': 'models', 'datasets': 'datasets', 'spaces': 'spaces'}[kind]
    url = 'https://huggingface.co/api/' + ep + '?author=' + ORG + '&limit=1000&full=false'
    items = []
    req = urllib.request.Request(url + '&paging=false', headers=H)
    with urllib.request.urlopen(req, timeout=120) as r:
        items = json.loads(r.read().decode('utf-8'))
    out = []
    for i in items:
        out.append({'id': i.get('id'), 'private': bool(i.get('private')),
                    'lastModified': i.get('lastModified'), 'likes': i.get('likes'),
                    'downloads': i.get('downloads'), 'pipeline_tag': i.get('pipeline_tag'),
                    'sdk': i.get('sdk')})
    return {'label': 'MEASURED', 'source': 'https://huggingface.co/api/' + ep + '?author=' + ORG,
            'fetched_at': now(), 'total': len(out),
            'private': [x['id'] for x in out if x['private']],
            'items': out}


def gh_census():
    raw = gh(['repo', 'list', GH_ORG, '--limit', '400', '--json',
              'name,isPrivate,description,updatedAt,primaryLanguage,stargazerCount'])
    repos = json.loads(raw)
    return {'label': 'MEASURED', 'source': 'gh repo list ' + GH_ORG,
            'fetched_at': now(), 'total': len(repos),
            'private': [r['name'] for r in repos if r.get('isPrivate')], 'items': repos}


def gh_open_prs():
    raw = gh(['api', 'search/issues', '-f', 'q=' + GH_ORG.lstrip('szl-holdings') and ('org:' + GH_ORG + ' type:pr state:open'), '-f', 'per_page=1', '--jq', '.total_count'])
    return {'label': 'MEASURED', 'source': 'gh api search/issues', 'fetched_at': now(),
            'open_prs': int(raw.strip())}


def gh_commit_estimate(repos_top):
    """Sum last-page Link header counts for the N most recently updated repos."""
    total = 0
    detail = {}
    for name in repos_top:
        try:
            r = subprocess.run(['gh', 'api', 'repos/%s/%s/commits?per_page=1' % (GH_ORG, name)],
                               capture_output=True, timeout=60)
            link = r.headers.get('Link') if hasattr(r, 'headers') else None
            # gh api does not expose headers in capture_output; use --jq on response of list endpoint in pages
            raw = gh(['api', 'repos/%s/%s/commits?per_page=1' % (GH_ORG, name), '--include'])
            for line in raw.splitlines():
                if line.startswith('link:') and 'rel="last"' in line:
                    for part in line.split(','):
                        if 'rel="last"' in part:
                            for seg in part.split('&'):
                                if seg.startswith('page='):
                                    total += int(seg.split('=')[1].rstrip('">'))
                                    detail[name] = int(seg.split('=')[1].rstrip('">'))
        except Exception:
            pass
    return {'label': 'MEASURED_SUBSET_TOP20_UPDATED', 'source': 'gh api commits Link last-page',
            'fetched_at': now(), 'repos_measured': sorted(detail),
            'commits_total_subset': total, 'detail': detail}


def hf_space_runtime(spaces):
    stages = {}
    for s in spaces:
        sid = s['id']
        try:
            req = urllib.request.Request('https://huggingface.co/api/spaces/' + sid + '/runtime', headers=H)
            with urllib.request.urlopen(req, timeout=30) as r:
                rt = json.loads(r.read().decode('utf-8'))
            stages[sid] = (rt.get('stage') or 'UNKNOWN')
        except Exception as e:
            stages[sid] = 'ERR:' + str(getattr(e, 'code', '?'))
        time.sleep(0.25)
    return {'label': 'MEASURED', 'source': 'hf /api/spaces/{id}/runtime', 'fetched_at': now(), 'stages': stages}


def mesh_evidence():
    """Snapshot of khipu-scholar-runs mesh receipts (single repo, paginated tree)."""
    files = []
    url = 'https://huggingface.co/api/datasets/' + ORG + '/khipu-scholar-runs/tree/main/mesh'
    while url:
        try:
            req = urllib.request.Request(url, headers=H)
            with urllib.request.urlopen(req, timeout=60) as r:
                page = json.loads(r.read().decode('utf-8'))
                link = r.headers.get('Link')
        except Exception:
            break
        files.extend([f.get('path') for f in page])
        url = None
        if link and 'rel="next"' in link:
            nxt = link.split('rel="next"')[0].split('<')[1].split('>')[0]
            url = nxt if nxt != url else None
    return {'label': 'MEASURED', 'fetched_at': now(),
            'source': 'hf khipu-scholar-runs tree mesh/', 'files': sorted(files)}


def chart_smoke():
    fails = []
    tests = {
        'line': charts.line_chart([{'name': 't', 'points': [(0, 3), (1, 2.2), (2, 1.4), (3, 1.1)]}], title='smoke'),
        'donut': charts.donut([('models', 413), ('datasets', 173), ('spaces', 79)]),
        'hbar': charts.hbar([('a', 30), ('b', 17)]),
        'spark': charts.sparkline([(0, 1), (1, 0.8)]),
    }
    import xml.dom.minidom
    for k, svg in tests.items():
        try:
            xml.dom.minidom.parseString(svg)
        except Exception as e:
            fails.append((k, str(e)[:120]))
    return {'label': 'MEASURED', 'checked': sorted(tests), 'failures': fails}


def main():
    ts = now().replace(':', '').replace('-', '')
    print('AUDIT_START', now(), flush=True)
    audit = {'generated_at': now(), 'weaver': 'estate-cards v0.1.0'}

    m = hf_census('models'); audit['hf_models'] = m
    d = hf_census('datasets'); audit['hf_datasets'] = d
    sp = hf_census('spaces'); audit['hf_spaces'] = sp

    bodies = {'models': m, 'datasets': d, 'spaces': sp}
    print('HF census: models', m['total'], 'datasets', d['total'], 'spaces', sp['total'], flush=True)

    audit['gh'] = gh_census()
    print('GH census:', audit['gh']['total'], flush=True)
    try:
        audit['gh_prs'] = gh_open_prs()
    except Exception as e:
        audit['gh_prs'] = {'label': 'UNKNOWN', 'err': repr(e)[:200]}
    try:
        updated = sorted(audit['gh']['items'], key=lambda r: r.get('updatedAt') or '', reverse=True)
        audit['gh_commits'] = gh_commit_estimate([r['name'] for r in updated[:20]])
    except Exception as e:
        audit['gh_commits'] = {'label': 'UNKNOWN', 'err': repr(e)[:200]}

    try:
        audit['space_runtime'] = hf_space_runtime(sp['items'])
    except Exception as e:
        audit['space_runtime'] = {'label': 'UNKNOWN', 'err': repr(e)[:200]}
    try:
        audit['mesh'] = mesh_evidence()
    except Exception as e:
        audit['mesh'] = {'label': 'UNKNOWN', 'err': repr(e)[:200]}

    audit['chart_smoke'] = chart_smoke()
    path = os.path.join(ROOT, 'data', 'audit-' + ts + '.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(audit, f, indent=1, ensure_ascii=False)
    with open(os.path.join(ROOT, 'data', 'audit-latest.json'), 'w', encoding='utf-8') as f:
        json.dump(audit, f, indent=1, ensure_ascii=False)
    print('AUDIT_DONE', now(), 'file', path, flush=True)
    print('SMOKE', json.dumps(audit['chart_smoke']), flush=True)


if __name__ == '__main__':
    main()
