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
from weaver import source_integrity

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


_README_UNOBSERVED = object()


def ndjson_commit(repo_id, kind, files, *, expected_readme=_README_UNOBSERVED):
    # LAST-MOMENT WRITE GATE: another source-owned publisher may pin README.md.
    # Even if the source manifest changes during this check, the immutable
    # parentCommit plus second source read must not allow a stale overwrite.
    wants_readme = any(name == 'README.md' for name, _ in files)
    if wants_readme:
        source_integrity.assert_readme_unbound(
            repo_id, kind, headers=cardbox.H,
        )
    parent = source_integrity.observed_head_sha(
        repo_id, kind, headers=cardbox.H,
    )
    if wants_readme:
        if expected_readme is _README_UNOBSERVED:
            raise source_integrity.SourceIntegrityHold('README_BASE_UNOBSERVED')
        source_integrity.assert_readme_unbound(
            repo_id, kind, headers=cardbox.H,
        )
        current = cardbox.fetch_readme(repo_id, kind)
        if current != expected_readme:
            raise source_integrity.SourceIntegrityHold('README_BASE_CHANGED')
    base_ep = 'https://huggingface.co/api/%s/%s/commit/main' % (
        {'model': 'models', 'dataset': 'datasets', 'space': 'spaces'}[kind], repo_id)
    nd = json.dumps({'key': 'header', 'value': {'summary': 'SZL estate showcase card (weaver v0.1.0, deterministic SVG charts)',
                                                'description': 'Source: github.com/szl-holdings/estate-cards. Receipt-honest append/refresh.',
                                                'parentCommit': parent}})
    for path, content in files:
        nd += chr(10) + json.dumps({'key': 'file', 'value': {'path': path, 'content': content}},
                                   ensure_ascii=False)
    body = nd.encode('utf-8')
    req = urllib.request.Request(
        base_ep, data=body, method='POST',
        headers={'Authorization': 'Bearer ' + TOKEN,
                 'Content-Type': 'application/x-ndjson'},
    )
    # Exactly one attempt: an interrupted POST may already have committed.
    # Never replay unknown outcomes or rate-limit responses under a stale
    # parent, and never leak provider response bodies into public receipts.
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            if r.status != 200:
                return int(r.status), 'COMMIT_HTTP_NON_200'
            return 200, 'PROVIDER_ACCEPTED_REQUIRES_SOURCE_READBACK'
    except urllib.error.HTTPError as e:
        return e.code, 'COMMIT_HTTP_REFUSED'
    except Exception:
        return 0, 'COMMIT_OUTCOME_UNKNOWN'


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
        if repo in done:
            continue
        try:
            cur = cardbox.fetch_readme(repo, kind)
            content, assets, mode = cardbox.build_card(kind, repo, audit, cur,
                                                        item.get('purpose'), item.get('meta_extra'))
            files = [('README.md', content)]
            for aname, svg in assets.items():
                files.append(('assets/szl-card/' + aname, svg))
            status, detail = ndjson_commit(
                repo, kind, files, expected_readme=cur,
            )
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
