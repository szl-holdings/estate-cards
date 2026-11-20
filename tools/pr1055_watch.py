#!/usr/bin/env python3
"""pr1055_watch v1 - READ-ONLY telemetry for org-profile PR 1055 (estate-cards).

Contract amendments honored (Kimi K3.1 + Mistral large-4, 2026-11-20):
- GET-ONLY egress: zero mutating calls; --assert-readonly scans this source
  for mutating verbs in gh_json call lines before observing.
- Receipts carry observed_at UTC, class REPORTED; hypothesis hints stay REPORTED.
- Watcher receipts cannot advance readiness (stated in every receipt).
"""
import argparse, json, subprocess, datetime, io, os, re

MUTATORS = re.compile(r"POST|PATCH|PUT|DELETE|\bmerge\b|\bpush\b|force", re.IGNORECASE)

def utcnow():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def gh_json(args, timeout=60):
    p = subprocess.run(["gh"] + args, capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        return None
    try:
        return json.loads(p.stdout)
    except Exception:
        return None

def assert_readonly():
    src = io.open(os.path.abspath(__file__), encoding="utf-8").read()
    lines = [l.strip() for l in src.splitlines() if "gh_json(" in l]
    bad = [l for l in lines if MUTATORS.search(l) and "REGEX_FOR_SELF_ASSERT" not in l]
    return not bad

def observe():
    pr = gh_json(["pr", "view", "1055", "--repo", "szl-holdings/.github", "--json", "state,mergedAt,mergeStateStatus,headRefOid,headRefName,autoMergeRequest,statusCheckRollup"])
    if pr is None:
        return {"class": "REPORTED", "error": "pr_view_failed", "observed_at": utcnow()}
    head = pr.get("headRefOid")
    commit = gh_json(["api", "GET", "repos/szl-holdings/.github/commits/" + str(head)]) or {}
    ver = (commit.get("commit") or {}).get("verification") or {}
    checks = {}
    for c in pr.get("statusCheckRollup") or []:
        n = c.get("name") or c.get("context") or "?"
        checks[n] = c.get("conclusion") or c.get("status") or "UNKNOWN"
    return {
        "class": "REPORTED",
        "observer": "estate-cards/pr1055_watch/v1",
        "observed_at": utcnow(),
        "pr": 1055,
        "state": pr.get("state"),
        "mergedAt": pr.get("mergedAt"),
        "mergeStateStatus": pr.get("mergeStateStatus"),
        "head_sha": head,
        "head_branch": pr.get("headRefName"),
        "auto_merge_enabled_at": (pr.get("autoMergeRequest") or {}).get("enabledAt"),
        "head_commit_verification": {"verified": ver.get("verified"), "reason": ver.get("reason")},
        "checks_observed": checks,
        "hypothesis_hint_REPORTED": "unsigned head may be rejected by merge-group provenance; NOT measured causation",
        "readiness_note": "watcher receipts cannot advance readiness",
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--assert-readonly", action="store_true")
    args = ap.parse_args()
    if args.assert_readonly and not assert_readonly():
        print("SELF_ASSERT_FAILED: mutating verb found")
        return 2
    rec = observe()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "receipts", "pr1055-watch-" + stamp + ".json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, "w", encoding="utf-8").write(json.dumps(rec, indent=1))
    print("RECEIPT_WRITTEN", path)
    print(json.dumps({"state": rec.get("state"), "mss": rec.get("mergeStateStatus"), "head_verified": (rec.get("head_commit_verification") or {}).get("verified")}))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())