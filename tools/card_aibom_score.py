#!/usr/bin/env python3
# card_aibom_score.py - AIBOM-completeness field-presence scorer (propose-only implement).
# Per Kimi governing ruling OPK1-20261124T033551Z item2 (GO_BUILD_PROPOSE_ONLY): stdlib-only,
# single-purpose, presence-accounting ONLY (no quality interpretation), fail-closed UNKNOWN,
# offline only. Axes per AIBOM completeness study arXiv 2607.17242 via merged PR #16 step 1.
# Implementation: plain line scanning, no regex.
import datetime
import json
import os
import sys

# field -> tokens (lowercase). Field PRESENT if any content line, stripped of heading marks,
# STARTS WITH a token, or the text contains token + colon.
FIELD_TOKENS = {
    "license": ("licen",),
    "datasets": ("dataset", "data sets"),
    "limitations": ("limitation",),
    "safety_risk": ("safety", "risk"),
    "environmental": ("environmental", "energy", "carbon"),
}


def score_text(text):
    # Return dict of field -> present bool. Line-based, no regex, never raises.
    present = {}
    stripped_lines = []
    for line in text.splitlines():
        s = line.strip()
        while s.startswith(chr(35)):
            s = s[1:].lstrip()
        stripped_lines.append(s.lower())
    low = text.lower()
    for field, tokens in FIELD_TOKENS.items():
        hit = False
        for tok in tokens:
            if (tok + chr(58)) in low:
                hit = True
                break
            for s in stripped_lines:
                if s.startswith(tok):
                    hit = True
                    break
            if hit:
                break
        present[field] = hit
    return present


def score_card(path):
    rec = {"card": os.path.basename(path)}
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception:
        rec["status"] = "UNKNOWN"
        rec["reason"] = "unparseable (read/decode fail)"
        rec["fields_present"] = None
        return rec
    if not text.strip():
        rec["status"] = "UNKNOWN"
        rec["reason"] = "empty"
        rec["fields_present"] = None
        return rec
    present = score_text(text)
    rec["status"] = "SCORED"
    rec["fields_present"] = present
    rec["present_count"] = sum(1 for v in present.values() if v)
    return rec


def run_on_paths(paths, out_dir, summary_note):
    recs = []
    for p in paths:
        recs.append(score_card(p))
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for rec in recs:
        name = os.path.splitext(rec["card"])[0]
        fn = os.path.join(out_dir, name + "." + stamp + ".aibom.json")
        with open(fn, "w", encoding="utf-8") as f:
            f.write(json.dumps({"stamp": stamp, "method": "field-presence only; no quality interpretation", **rec}, indent=2))
    scored = [r for r in recs if r["status"] == "SCORED"]
    unknown = [r["card"] for r in recs if r["status"] == "UNKNOWN"]
    summary = {
        "stamp": stamp,
        "method": "AIBOM field-presence scoring (license, datasets, limitations, safety_risk, environmental); presence accounting only",
        "disclaimer": "scores are field-presence measurements, NOT model quality/safety/compliance/readiness judgments",
        "cards_total": len(recs), "cards_scored": len(scored), "cards_unknown": len(unknown),
        "unknown_cards": unknown,
        "field_presence_counts": {f: sum(1 for r in scored if r["fields_present"].get(f)) for f in FIELD_TOKENS},
        "note": summary_note,
    }
    spath = os.path.join(out_dir, "summary." + stamp + ".json")
    with open(spath, "w", encoding="utf-8") as f:
        f.write(json.dumps(summary, indent=2))
    return summary, spath


def gather_cards(root, limit=60):
    paths = []
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in (".git", "node_modules", "__pycache__", "receipts", "docs")]
        depth = os.path.relpath(d, root).count(os.sep)
        if depth > 2:
            dirs[:] = []
            continue
        for f in sorted(files):
            if f.lower().endswith(".md") and not f.lower().startswith("receipt"):
                paths.append(os.path.join(d, f))
    return paths[:limit]


def main():
    if len(sys.argv) < 2:
        print("usage: card_aibom_score.py <repo-root> [out-dir]")
        return 2
    root = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(root, "tools", "receipts", "aibom")
    os.makedirs(out_dir, exist_ok=True)
    cards = gather_cards(root)
    summary, spath = run_on_paths(cards, out_dir, "offline run on estate-cards own card files")
    print(json.dumps(summary, indent=2))
    print("SUMMARY_PATH " + spath)
    return 0


if __name__ == "__main__":
    sys.exit(main())
