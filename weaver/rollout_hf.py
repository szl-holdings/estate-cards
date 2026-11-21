"""Paced HF card roller: queue-driven, resumable, receipted, fail-closed.

- queue file: queue.jsonl  lines {kind, repo, purpose?, meta_extra?}
- 14s+ between commits (stays under the measured ~320/h org quota), 429 backoff
- receipts: rollout_receipts.jsonl (one line per attempted repo)
- STOP file halts; done-set resumes cleanly
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import os
import time
import urllib.request
import urllib.error
import datetime

from weaver import cards as cardbox
from weaver import policy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Q = os.path.join(ROOT, 'queue.jsonl')
RCPT = os.path.join(ROOT, 'rollout_receipts.jsonl')
STATE = os.path.join(ROOT, 'rollout_state.json')
STOP = os.path.join(ROOT, 'STOP')
TOKEN = open('C:/Users/steph/.cache/huggingface/token', encoding='utf-8').read().strip()
COMMIT_EP = 'https://huggingface.co/api/datasets/%s/commit/main'


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def log(rec):
    rec = dict(rec); rec['ts'] = now()
    with open(RCPT, 'a', encoding='utf-8') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + chr(10))


def ndjson_commit(repo_id, kind, files):
    base_ep = 'https://huggingface.co/api/%s/%s/commit/main' % (
        {'model': 'models', 'dataset': 'datasets', 'space': 'spaces'}[kind], repo_id)
    nd = json.dumps({'key': 'header', 'value': {'summary': 'SZL estate showcase card (weaver v0.1.0, deterministic SVG charts)',
                                                'description': 'Source: github.com/szl-holdings/estate-cards. Receipt-honest append/refresh.'}})
    for path, content in files:
        nd += chr(10) + json.dumps({'key': 'file', 'value': {'path': path, 'content': content}},
                                   ensure_ascii=False)
    body = nd.encode('utf-8')
    for attempt in range(6):
        try:
            req = urllib.request.Request(base_ep, data=body, method='POST',
                                         headers={'Authorization': 'Bearer ' + TOKEN,
                                                  'Content-Type': 'application/x-ndjson'})
            with urllib.request.urlopen(req, timeout=180) as r:
                return r.status, r.read().decode('utf-8')[:300]
        except urllib.error.HTTPError as e:
            detail = e.read().decode('utf-8')[:200]
            if e.code == 429:
                wait = min(60 * (2 ** attempt), 1200)
                time.sleep(wait)
                continue
            return e.code, detail
        except Exception as e:
            time.sleep(15)
            detail = repr(e)[:200]
    return 0, 'exhausted retries'


def load_state():
    if os.path.exists(STATE):
        return json.load(open(STATE, encoding='utf-8'))
    return {'done': []}


def main():
    if not os.path.exists(Q):
        print('NO_QUEUE', flush=True)
        return
    audit = json.load(open(os.path.join(ROOT, 'data', 'audit-latest.json'), encoding='utf-8'))
    st = load_state()
    done = set(st['done'])
    with open(Q, encoding='utf-8') as f:
        items = [json.loads(l) for l in f if l.strip()]
    print('QUEUE', len(items), 'done', len(done), flush=True)
    for item in items:
        if os.path.exists(STOP):
            print('STOP_FILE', flush=True); break
        repo = item['repo']; kind = item['kind']
        if policy.source_managed(kind, repo):
            log({'repo': repo, 'kind': kind, 'status': 'skipped_source_managed'})
            continue
        if repo in done:
            continue
        try:
            cur = cardbox.fetch_readme(repo, kind)
            content, assets, mode = cardbox.build_card(kind, repo, audit, cur,
                                                        item.get('purpose'), item.get('meta_extra'))
            files = [('README.md', content)]
            for aname, svg in assets.items():
                files.append(('assets/szl-card/' + aname, svg))
            status, detail = ndjson_commit(repo, kind, files)
            ok = status == 200
            log({'repo': repo, 'kind': kind, 'mode': mode, 'commit_status': status,
                 'ok': ok, 'detail': detail[:160] if not ok else ''})
            print('ROLL', repo, mode, status, flush=True)
            if ok:
                done.add(repo)
                json.dump({'done': sorted(done)}, open(STATE, 'w', encoding='utf-8'))
            time.sleep(14)
        except Exception as e:
            log({'repo': repo, 'ok': False, 'err': repr(e)[:300]})
            print('ERR', repo, repr(e)[:150], flush=True)
            time.sleep(8)
    print('ROLLOUT_PASS_DONE', now(), flush=True)


if __name__ == '__main__':
    main()
