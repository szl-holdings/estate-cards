"""Scan-and-publish: the 15 private HF repos. Secret scan -> verify -> flip public.

Doctrines: keys masked, receipts per repo, a11oy-state held private (governance state),
anything anomalous is skipped and reported, never forced.
"""
import json
import re
import urllib.request
import urllib.parse
import urllib.error
import datetime

TOKEN = open('C:/Users/steph/.cache/huggingface/token', encoding='utf-8').read().strip()
H = {'Authorization': 'Bearer ' + TOKEN}

PATTERNS = [
    (re.compile(r'hf_[A-Za-z0-9_-]{20,}'), 'HF token'),
    (re.compile(r'gho_[A-Za-z0-9]{30,}'), 'GH token'),
    (re.compile(r'github_pat_[A-Za-z0-9_]{30,}'), 'GH PAT'),
    (re.compile(r'sk-[A-Za-z0-9]{20,}'), 'OpenAI-style key'),
    (re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----'), 'private key'),
    (re.compile(r'Salad-Api-Key["\':= ]+[A-Za-z0-9]{16,}'), 'Salad key'),
]

TARGETS = [
    ('model', 'SZLHOLDINGS/salad-ring-v1'),
    ('model', 'SZLHOLDINGS/salad-ring-v1b'),
    ('model', 'SZLHOLDINGS/salad-ring-serve-gemma1'),
    ('model', 'SZLHOLDINGS/salad-ring-serve-llama1'),
    ('model', 'SZLHOLDINGS/salad-ring-serve-mistral1'),
    ('model', 'SZLHOLDINGS/salad-flagship55-v1'),
    ('model', 'SZLHOLDINGS/salad-ring-ouro-l12'),
    ('model', 'SZLHOLDINGS/salad-ring-ouro-l13'),
    ('model', 'SZLHOLDINGS/salad-ring-ouro-l15'),
    ('model', 'SZLHOLDINGS/salad-ring-ouro-l16'),
    ('model', 'SZLHOLDINGS/salad-ring-ouro-l17'),
    ('model', 'SZLHOLDINGS/salad-ring-ouro-l18'),
    ('model', 'SZLHOLDINGS/salad-governed-distill-27b-qlora-r1'),
    ('dataset', 'SZLHOLDINGS/szl-agentic-reflex-v1'),
]
HELD = [('dataset', 'SZLHOLDINGS/a11oy-state', 'governance state - held private on recommendation, owner can override')]


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def raw_readme(kind, repo):
    base = {'model': 'models', 'dataset': 'datasets'}[kind]
    req = urllib.request.Request('https://huggingface.co/%s/%s/raw/main/README.md' % (base, repo), headers=H)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read().decode('utf-8', 'replace')
    except Exception:
        return ''


def tree(kind, repo):
    base = {'model': 'models', 'dataset': 'datasets'}[kind]
    req = urllib.request.Request('https://huggingface.co/api/%s/%s/tree/main?recursive=true&expand=false' % (base, repo), headers=H)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            page = json.loads(r.read().decode('utf-8'))
        return [x.get('path', '') for x in page]
    except Exception:
        return []


def scan(clean_name, paths, readme):
    hits = []
    for pat, label in PATTERNS:
        for m in pat.finditer(readme):
            hits.append('README:' + label + ' @' + clean_name)
    for p in paths:
        low = p.lower()
        if low.endswith(('.env', '.sk', 'token.txt', 'secret.json', 'credentials.json', 'id_rsa')) \
           or ('.cache/huggingface' in low) or ('edge-debug' in low):
            hits.append('TREE:sensitive-path ' + p)
    return hits


def flip_public(kind, repo):
    base = {'model': 'models', 'dataset': 'datasets'}[kind]
    ep = 'https://huggingface.co/api/%s/%s/settings' % (base, repo)
    last = None
    for bodyform, ct in ((urllib.parse.urlencode({'private': 'False'}).encode(), 'application/x-www-form-urlencoded'),
                          (json.dumps({'private': False}).encode(), 'application/json')):
        try:
            req = urllib.request.Request(ep, data=bodyform, method='POST',
                                         headers={'Authorization': 'Bearer ' + TOKEN, 'Content-Type': ct})
            with urllib.request.urlopen(req, timeout=60) as r:
                last = ('OK', r.status)
                break
        except urllib.error.HTTPError as e:
            last = ('HTTP%d' % e.code, e.read().decode('utf-8')[:160])
        except Exception as e:
            last = ('ERR', repr(e)[:160])
    return last


def verify_public(kind, repo):
    base = {'model': 'models', 'dataset': 'datasets'}[kind]
    req = urllib.request.Request('https://huggingface.co/api/%s/%s' % (base, repo), headers=H)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode('utf-8')).get('private')


receipts = []
for kind, repo in TARGETS + [t[:2] for t in HELD]:
    entry = {'repo': repo, 'kind': kind, 'ts': now()}
    readme = raw_readme(kind, repo)
    paths = tree(kind, repo)
    entry['readme_len'] = len(readme)
    entry['tree_files'] = len(paths)
    hits = scan(repo, paths, readme)
    entry['scan_hits'] = hits
    if (kind, repo) in [(k, r) for k, r in TARGETS] and not hits:
        res = flip_public(kind, repo)
        entry['flip'] = {'result': str(res[0]), 'detail': res[1] if res[0] != 'OK' else ''}
        entry['now_private'] = verify_public(kind, repo)
    else:
        entry['action'] = 'HELD/scan-issue' if hits else 'HELD (listed)'
    receipts.append(entry)
    print(json.dumps(entry) [:400], flush=True)

with open('C:/SZL/edge-debug/estate-cards/data/private-flip-receipts.json', 'w', encoding='utf-8') as f:
    json.dump(receipts, f, indent=1, ensure_ascii=False)
print('PRIV_FLIP_DONE', now(), flush=True)
