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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Q = os.path.join(ROOT, 'queue.jsonl')
RCPT = os.path.join(ROOT, 'rollout_receipts.jsonl')
STATE = os.path.join(ROOT, 'rollout_state.json')
STOP = os.path.join(ROOT, 'STOP')
def _publisher_token():
    # Explicit owner-supplied credential only; never scrape a workstation token file.
    token = os.environ.get("SZL_HF_CARD_PUBLISH_TOKEN", "").strip()
    if not token:
        raise RuntimeError("EXPLICIT_CARD_PUBLISH_TOKEN_REQUIRED")
    return token

def _target_admitted(repo_id, kind):
    # A queue entry, a publish credential and a global --apply are not approval.
    # A separately injected exact target scopes a single operator-reviewed run.
    return os.environ.get("SZL_HF_CARD_APPROVED_TARGET", "").strip() == f"{kind}:{repo_id}"


COMMIT_EP = 'https://huggingface.co/api/datasets/%s/commit/main'


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def log(rec):
    rec = dict(rec); rec['ts'] = now()
    with open(RCPT, 'a', encoding='utf-8') as f:
        f.write(json.dumps(rec, ensure_ascii=False) + chr(10))


def ndjson_commit(repo_id, kind, files, *, approved=False):
    # A Space README may be listed in SOURCE.json. Editing it outside the canonical
    # GitHub -> HF source publisher can make the running container fail at import.
    if kind == "space":
        return 403, "SOURCE_OWNED_SPACE_PUBLISHER_REQUIRED"
    if kind not in ("model", "dataset"):
        return 403, "INVALID_REPOSITORY_KIND"
    if not approved or not _target_admitted(repo_id, kind):
        return 403, "EXPLICIT_OWNER_CARD_ADMISSION_REQUIRED"

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
                                         headers={'Authorization': 'Bearer ' + _publisher_token(),
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


def main(argv=None):
    args = sys.argv[1:] if argv is None else list(argv)
    if not args:
        apply, approved_repo = False, None
    elif len(args) == 3 and args[:2] == ["--apply", "--repo"]:
        apply, approved_repo = True, args[2]
        # One immutable repository selector, never an entire queued estate.
        if (not isinstance(approved_repo, str) or not approved_repo.startswith("SZLHOLDINGS/")
                or approved_repo.count("/") != 1 or len(approved_repo) > 128
                or not approved_repo.split("/", 1)[1]
                or not all(c.isalnum() or c in "-_" for c in approved_repo.split("/", 1)[1])):
            raise ValueError("USAGE: invalid exact --repo target")
    else:
        raise ValueError("USAGE: rollout_hf.py [--apply --repo SZLHOLDINGS/NAME]")

    if not os.path.exists(Q):
        print('NO_QUEUE', flush=True)
        return
    with open(os.path.join(ROOT, 'data', 'audit-latest.json'), encoding='utf-8') as audit_file:
        audit = json.load(audit_file)
    st = load_state()
    done = set(st['done'])
    with open(Q, encoding='utf-8') as f:
        items = [json.loads(l) for l in f if l.strip()]
    if apply and sum(isinstance(item, dict) and item.get("repo") == approved_repo for item in items) != 1:
        raise ValueError("EXPLICIT_APPROVED_REPOSITORY_MISSING_OR_DUPLICATE")
    print('QUEUE', len(items), 'done', len(done), flush=True)
    for item in items:
        # Never touch unrelated queue rows, even if an operator supplied a token.
        if apply and item.get("repo") != approved_repo:
            continue
        if os.path.exists(STOP):
            print('STOP_FILE', flush=True); break
        repo = item.get('repo'); kind = item.get('kind')
        # No auto-approval from an estate-wide instruction or a queue row.
        # Source-owned Spaces MUST publish cards through their authorized GitHub
        # manifests and maintenance-window workflow, never a parallel Hub writer.
        if not isinstance(repo, str) or not repo.startswith('SZLHOLDINGS/') or (
                len(repo) > 128 or not all(c.isalnum() or c in '-_/' for c in repo)):
            log({'repo': str(repo)[:128], 'kind': kind, 'decision': 'INVALID_REPOSITORY', 'ok': False})
            continue
        if kind == 'space':
            log({'repo': repo, 'kind': kind, 'decision': 'SOURCE_OWNED_SPACE_PUBLISHER_REQUIRED', 'ok': False})
            print('SKIP_SOURCE_OWNED_SPACE', repo, flush=True)
            continue
        if kind not in ('model', 'dataset'):
            log({'repo': repo, 'kind': kind, 'decision': 'INVALID_REPOSITORY_KIND', 'ok': False})
            continue
        if repo in done:
            continue
        if not apply:
            log({'repo': repo, 'kind': kind, 'decision': 'DRY_RUN_REVIEW_REQUIRED', 'ok': False})
            continue
        if not _target_admitted(repo, kind):
            log({'repo': repo, 'kind': kind, 'decision': 'EXPLICIT_OWNER_CARD_ADMISSION_REQUIRED', 'ok': False})
            print('HOLD_NO_PER_REPOSITORY_ADMISSION', flush=True)
            break
        if not os.environ.get('SZL_HF_CARD_PUBLISH_TOKEN', '').strip():
            log({'repo': repo, 'kind': kind, 'decision': 'EXPLICIT_CARD_PUBLISH_TOKEN_REQUIRED', 'ok': False})
            print('HOLD_NO_EXPLICIT_PUBLISH_TOKEN', flush=True)
            break
        try:
            cur = cardbox.fetch_readme(repo, kind)
            # A 429/403/timeout is indistinguishable from absent README in the
            # legacy reader. Never compose over unknown existing model metadata.
            if cur is None:
                raise RuntimeError('README_READ_UNAVAILABLE_FAIL_CLOSED')
            content, assets, mode = cardbox.build_card(kind, repo, audit, cur,
                                                        item.get('purpose'), item.get('meta_extra'))
            files = [('README.md', content)]
            for aname, svg in assets.items():
                files.append(('assets/szl-card/' + aname, svg))
            status, detail = ndjson_commit(repo, kind, files, approved=apply)
            ok = status == 200
            log({'repo': repo, 'kind': kind, 'mode': mode, 'commit_status': status,
                 'ok': ok, 'detail': detail[:160] if not ok else ''})
            print('ROLL', repo, mode, status, flush=True)
            if ok:
                done.add(repo)
                with open(STATE, 'w', encoding='utf-8') as state_file:
                    json.dump({'done': sorted(done)}, state_file)
            time.sleep(14)
        except Exception as e:
            log({'repo': repo, 'ok': False, 'err': repr(e)[:300]})
            print('ERR', repo, repr(e)[:150], flush=True)
            time.sleep(8)
    print('ROLLOUT_PASS_DONE', now(), flush=True)


if __name__ == '__main__':
    main()
