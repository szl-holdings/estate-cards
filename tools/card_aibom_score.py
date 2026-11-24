#!/usr/bin/env python3
"""card_aibom_score.py - AIBOM-completeness field-presence scorer (propose-only implement).

Per Kimi governing ruling OPK1-20261124T033551Z (GO_BUILD_PROPOSE_ONLY): stdlib-only, single-purpose,
presence-accounting ONLY (no quality/safety/compliance interpretation), fail-closed
UNKNOWN on unparseable cards (never guessed), offline only.
Field axes follow the AIBOM completeness study (arXiv 2607.17242): license,
datasets, limitations, safety-risk, environmental - via merged estate-cards leader
study PR #16 absorb plan step 1.
"""
import json
import os
import re
import sys
import datetime

FIELDS = {
    "license": re.compile(r"(?im)^#*\s*licen[cs]e|(?i)licen[cs]e\s*:"),
    "datasets": re.compile(r"(?im)^#*\s*datasets?|(?i)datasets?\s*:"),
    "limitations": re.compile(r"(?im)^#*\s*limitations?|(?i)limitations?\s*:"),
    "safety_risk": re.compile(r"(?im)^#*\s*(safety|risks?)|(?i)(safety[_ -]??risk|safety)\s*:"),
    "environmental": re.compile(r"(?im)^#*\s*(environmental|energy|carbon)|(?i)(environmental|energy)\s*:"),
}


def score_text(text):
    """Return dict of field -> present bool. Never raises on weird text."""
    present = {}
    low = text.lower()
    for field, rx in FIELDS.items():
        try:
            present[field] = bool(rx.search(text))
        except Exception:
            present[field] = False
    # frontmatter license: is common; require word context to avoid pure substring noise
    if "licen" not in low:
        present["license"] = False
    return present


def score_card(path):
    """Score one card file. Fail-closed: unparseable -> status UNKNOWN."""
    rec = {"card": os.path.basename(path)}
    try:
        with open(path, "r", encoding="utf-8", errors="strict") as f:
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


def run_on_paths(paths, out_dir, summary_note=""):
    recs = []
    for p in paths:
        rec = score_card(p)
        recs.append(rec)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for rec in recs:
        name = os.path.splitext(rec["card"])[0]
        with open(os.path.join(out_dir, name + "." + stamp + ".aibom.json"), "w", encoding="utf-8") as f:
            f.write(json.dumps({"stamp": stamp, "method": "field-presence only; no quality interpretation",
                                **rec}, indent=2))
    scored = [r for r in recs if r["status"] == "SCORED"]
    unknown = [r["card"] for r in recs if r["status"] == "UNKNOWN"]
    summary = {"stamp": stamp,
               "method": "AIBOM field-presence scoring (license, datasets, limitations, safety_risk, environmental); presence accounting only",
               "disclaimer": "scores are field-presence measurements, NOT model quality/safety/compliance/readiness judgments",
               "cards_total": len(recs), "cards_scored": len(scored), "cards_unknown": len(unknown),
               "unknown_cards": unknown,
               "field_presence_counts": {f: sum(1 for r in scored if r["fields_present"].get(f)) for f in FIELDS},
               "note": summary_note}
    spath = os.path.join(out_dir, "summary." + stamp + ".json")
    with open(spath, "w", encoding="utf-8") as f:
        f.write(json.dumps(summary, indent=2))
    return summary, spath


def gather_cards(root, limit=60):
    """Candidate card files: markdown at shallow depth (depth<=2), excluding docs/receipts dirs."""
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
    summary, spath = run_on_paths(cards, out_dir, summary_note="offline run on estate-cards own card files")
    print(json.dumps(summary, indent=2))
    print("SUMMARY_PATH " + spath)
    return 0


if __name__ == "__main__":
    sys.exit(main())
