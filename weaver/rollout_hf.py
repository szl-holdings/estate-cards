"""Paced HF card roller: queue-driven, resumable, receipted, fail-closed.

- queue file: queue.jsonl  lines {kind, repo, purpose?, meta_extra?}
- 14s+ between commits; ambiguous provider writes NEVER auto-retried
- receipts: rollout_receipts.jsonl (one line per attempted repo)
- STOP file halts; done-set resumes cleanly
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import os
import re
import time
import urllib.request
import urllib.error
import datetime

from weaver import cards as cardbox
from weaver.source_guard import Hold as SourceGuardHold, REPO_ID as HUB_REPO_ID, check as source_preflight

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Q = os.path.join(ROOT, 'queue.jsonl')
RCPT = os.path.join(ROOT, 'rollout_receipts.jsonl')
STATE = os.path.join(ROOT, 'rollout_state.json')
STOP = os.path.join(ROOT, 'STOP')
def _write_token():
    # Never read a publisher credential until the public source guard admits a write.
    try:
        with open('C:/Users/steph/.cache/huggingface/token', encoding='utf-8') as stream:
            token = stream.read().strip()
    except OSError:
        raise SourceGuardHold('HUB_WRITE_CREDENTIAL_UNAVAILABLE') from None
    if not token:
        raise SourceGuardHold('HUB_WRITE_CREDENTIAL_UNAVAILABLE')
    return token
COMMIT_EP = 'https://huggingface.co/api/datasets/%s/commit/main'


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def log(rec):
    rec = dict(rec); rec['ts'] = now()
    with open(RCPT, 'a', encoding='utf-8') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + chr(10))


def ndjson_commit(repo_id, kind, files, parent_commit):
    # A portfolio/card writer never owns executable Space source files.
    if kind == 'space':
        raise SourceGuardHold('SPACE_CANONICAL_PUBLISHER_REQUIRED')
    if kind not in ('model', 'dataset') or not isinstance(repo_id, str) or not HUB_REPO_ID.fullmatch(repo_id):
        raise SourceGuardHold('HUB_REPOSITORY_IDENTITY_INVALID')
    if not isinstance(parent_commit, str) or not re.fullmatch(r'[0-9a-f]{40}', parent_commit):
        raise SourceGuardHold('HUB_COMMIT_PARENT_UNAVAILABLE')
    token = _write_token()
    base_ep = 'https://huggingface.co/api/%s/%s/commit/main' % (
        {'model': 'models', 'dataset': 'datasets', 'space': 'spaces'}[kind], repo_id)
    nd = json.dumps({'key': 'header', 'value': {'summary': 'SZL estate showcase card (weaver v0.1.0, deterministic SVG charts)',
                                                'description': 'Source: github.com/szl-holdings/estate-cards. Receipt-honest append/refresh.',
                                                'parentCommit': parent_commit}})
    for path, content in files:
        nd += chr(10) + json.dumps({'key': 'file', 'value': {'path': path, 'content': content}},
                                   ensure_ascii=False)
    body = nd.encode('utf-8')
    # A transport failure may follow a committed provider mutation. Do not
    # retry a POST whose outcome cannot be independently reconciled.
    try:
        req = urllib.request.Request(base_ep, data=body, method='POST',
                                     headers={'Authorization': 'Bearer ' + token,
                                              'Content-Type': 'application/x-ndjson'})
        with urllib.request.urlopen(req, timeout=180) as r:
            return r.status, r.read().decode('utf-8')[:300]
    except urllib.error.HTTPError as exc:
        # Including 429: no verified no-commit readback exists here.
        return exc.code, 'HTTP_PROVIDER_REFUSAL_NO_AUTOMATIC_RESEND'
    except Exception:
        return 0, 'PROVIDER_OUTCOME_UNKNOWN_NO_AUTOMATIC_RESEND'


def load_state():
    if os.path.exists(STATE):
        with open(STATE, encoding='utf-8') as stream:
            return json.load(stream)
    return {'done': []}


def main():
    if not os.path.exists(Q):
        print('NO_QUEUE', flush=True)
        return
    with open(os.path.join(ROOT, 'data', 'audit-latest.json'), encoding='utf-8') as stream:
        audit = json.load(stream)
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
            # Before *any* card fetch, do not touch another Space's runnable code.
            if kind == 'space':
                raise SourceGuardHold('SPACE_CANONICAL_PUBLISHER_REQUIRED')
            # Public metadata-only owner guard; pin CAS to that exact Hub revision.
            parent = source_preflight(repo, kind)
            cur = cardbox.fetch_readme(repo, kind, parent_revision=parent)
            content, assets, mode = cardbox.build_card(kind, repo, audit, cur,
                                                        item.get('purpose'), item.get('meta_extra'))
            files = [('README.md', content)]
            for aname, svg in assets.items():
                files.append(('assets/szl-card/' + aname, svg))
            status, detail = ndjson_commit(repo, kind, files, parent)
            ok = status == 200
            log({'repo': repo, 'kind': kind, 'mode': mode, 'commit_status': status,
                 'ok': ok, 'detail': detail[:160] if not ok else ''})
            print('ROLL', repo, mode, status, flush=True)
            if ok:
                done.add(repo)
                with open(STATE, 'w', encoding='utf-8') as stream:
                    json.dump({'done': sorted(done)}, stream)
            time.sleep(14)
        except SourceGuardHold as exc:
            log({'repo': repo, 'kind': kind, 'ok': False,
                 'admission': 'HOLD', 'reason': str(exc)})
            print('HOLD', repo, str(exc), flush=True)
            continue
        except Exception as e:
            log({'repo': repo, 'ok': False, 'err': repr(e)[:300]})
            print('ERR', repo, repr(e)[:150], flush=True)
            time.sleep(8)
    print('ROLLOUT_PASS_DONE', now(), flush=True)


if __name__ == '__main__':
    main()
