import json, urllib.request, urllib.request, urllib.error, datetime
TOKEN = open('C:/Users/steph/.cache/huggingface/token', encoding='utf-8').read().strip()

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
HELD = ['SZLHOLDINGS/a11oy-state']

def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

def base_api(kind):
    return 'https://huggingface.co/api/' + ('models' if kind == 'model' else 'datasets')

def get_private(kind, repo):
    req = urllib.request.Request(base_api(kind) + '/' + repo, headers={'Authorization': 'Bearer ' + TOKEN})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode('utf-8')).get('private')

def flip(kind, repo):
    ep = base_api(kind) + '/' + repo + '/settings'
    req = urllib.request.Request(ep, data=json.dumps({'private': False}).encode(), method='PUT',
                                 headers={'Authorization': 'Bearer ' + TOKEN, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status

receipts = []
held_recs = []
for kind, repo in TARGETS:
    p = get_private(kind, repo)
    if p is False:
        receipts.append({'repo': repo, 'already_public': True, 'ts': now()})
        print('ALREADY_PUBLIC', repo, flush=True)
        continue
    try:
        st = flip(kind, repo)
        p2 = get_private(kind, repo)
        receipts.append({'repo': repo, 'status': st, 'now_private': p2, 'ts': now()})
        print('FLIPPED', repo, st, 'private=', p2, flush=True)
    except Exception as e:
        receipts.append({'repo': repo, 'err': repr(e)[:200], 'ts': now()})
        print('FLIP_ERR', repo, repr(e)[:120], flush=True)
for repo in HELD:
    held_recs.append({'repo': repo, 'held': 'recommendation: governance state', 'ts': now()})
with open('C:/SZL/edge-debug/estate-cards/data/private-flip-receipts-2.json', 'w', encoding='utf-8') as f:
    json.dump({'flips': receipts, 'held': held_recs, 'done': now()}, f, indent=1)
print('FLIP_PASS_DONE', now(), flush=True)
