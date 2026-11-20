#!/usr/bin/env python3
"""Fail-closed, read-only audit of the pinned 2026-11-20 rollout."""

from __future__ import annotations

import json
import py_compile
import re
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
RECEIPTS_PATH = ROOT / "data" / "rollout_receipts.jsonl"
QUEUE_PATH = ROOT / "data" / "queue.jsonl"
WATCH_PATH = ROOT / "tools" / "pr1055_watch.py"
WATCH_TRACKED = "tools/pr1055_watch.py"

RECEIPT_KEYS = frozenset({"ts","kind","repo","mode","detail","commit_status","ok"})
EXPECTED_RECEIPT_KINDS = Counter({"model": 400, "dataset": 170, "space": 77})
EXPECTED_QUEUE_KINDS = Counter({"model": 400, "dataset": 171, "space": 79})
EXPECTED_MODES = Counter({"compose": 426, "append": 221})
EXPECTED_FIRST_TS = "2026-11-20T03:50:37Z"
EXPECTED_LAST_TS = "2026-11-20T06:27:00Z"
CANONICAL_DATA = frozenset(
    {"data/rollout_receipts.jsonl", "data/queue.jsonl"}
)

TS_RE = re.compile(r"^2026-11-20T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")

# Cleaner restore 2026-11-20: spec (run-1 verified) bans MUTATING commands only;
# the watcher legitimately uses subprocess for GET-only gh calls.
FORBIDDEN_TOKENS = (
    "gh pr merge",
    "gh pr edit",
    "gh api -X POST",
    "gh api -X PATCH",
    "gh api -X DELETE",
    "git push",
    "gh repo delete",
    '"git"',
)


class CheckFailure(Exception):
    """An expected check failure; remaining checks must still run."""


@dataclass
class Context:
    receipts: list[dict[str, Any]]
    queue: list[dict[str, Any]]
    errors: dict[str, str]


CheckFunction = Callable[[Context], str]
CHECKS: list[tuple[str, CheckFunction]] = []


def check(label: str) -> Callable[[CheckFunction], CheckFunction]:
    def decorate(function: CheckFunction) -> CheckFunction:
        CHECKS.append((label, function))
        return function

    return decorate


def require(condition: bool, detail: str) -> None:
    if not condition:
        raise CheckFailure(detail)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                raise ValueError("blank/whitespace-only JSONL line")
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: JSON value is not an object")
            rows.append(value)
    return rows


def receipt_rows(ctx: Context) -> list[dict[str, Any]]:
    if "receipts" in ctx.errors:
        raise CheckFailure(f"load_receipts={ctx.errors['receipts']}")
    return ctx.receipts


def queue_rows(ctx: Context) -> list[dict[str, Any]]:
    if "queue" in ctx.errors:
        raise CheckFailure(f"load_queue={ctx.errors['queue']}")
    return ctx.queue


def git_text(*args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(ROOT), *args],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or f"git exit {completed.returncode}"
        raise CheckFailure(f"git_{args[0]}={message}")
    return completed.stdout


def git_lines(*args: str) -> list[str]:
    return [line for line in git_text(*args).splitlines() if line]


@check("1.01")
def check_101(ctx: Context) -> str:
    rows = receipt_rows(ctx)
    require(len(rows) == 647, f"rows={len(rows)} expected=647")
    return f"rows={len(rows)}"


@check("1.02")
def check_102(ctx: Context) -> str:
    rows = receipt_rows(ctx)
    objects = sum(isinstance(row, dict) for row in rows)
    require(objects == 647, f"object_rows={objects} expected=647")
    return f"object_rows={objects}"


@check("1.03")
def check_103(ctx: Context) -> str:
    rows = receipt_rows(ctx)
    ok_true = sum(row.get("ok") is True for row in rows)
    commit_status_200 = sum(row.get("commit_status") == 200 for row in rows)
    require(
        ok_true == 647 and commit_status_200 == 647,
        f"ok_true={ok_true} commit_status_200={commit_status_200}",
    )
    return f"ok_true={ok_true} commit_status_200={commit_status_200}"


@check("1.04")
def check_104(ctx: Context) -> str:
    rows = receipt_rows(ctx)
    valid = sum(frozenset(row) == RECEIPT_KEYS for row in rows)
    require(valid == 647, f"valid_key_rows={valid} expected=647")
    return f"valid_key_rows={valid}"


@check("1.05")
def check_105(ctx: Context) -> str:
    rows = receipt_rows(ctx)
    valid = 0
    for row in rows:
        if frozenset(row) != RECEIPT_KEYS:
            continue
        if not all(isinstance(row[key], str) for key in ("ts", "kind", "repo", "mode", "detail")):
            continue
        if type(row["commit_status"]) is not int or type(row["ok"]) is not bool:
            continue
        if not row["repo"] or row["repo"] != row["repo"].strip():
            continue
        valid += 1
    require(valid == 647, f"valid_field_rows={valid} expected=647")
    return f"valid_field_rows={valid}"


@check("1.06")
def check_106(ctx: Context) -> str:
    rows = receipt_rows(ctx)
    unique = len({row.get("repo") for row in rows})
    require(unique == 647, f"unique={unique} expected=647")
    return f"unique={unique}"


@check("1.07")
def check_107(ctx: Context) -> str:
    rows = receipt_rows(ctx)
    kinds = Counter(row.get("kind") for row in rows)
    require(kinds == EXPECTED_RECEIPT_KINDS, f"kinds={dict(kinds)}")
    return (
        f"model={kinds['model']} dataset={kinds['dataset']} "
        f"space={kinds['space']}"
    )


@check("1.08")
def check_108(ctx: Context) -> str:
    rows = receipt_rows(ctx)
    modes = Counter(row.get("mode") for row in rows)
    require(modes == EXPECTED_MODES, f"modes={dict(modes)}")
    return f"compose={modes['compose']} append={modes['append']}"


@check("1.09")
def check_109(ctx: Context) -> str:
    rows = receipt_rows(ctx)
    valid = sum(
        isinstance(row.get("ts"), str) and TS_RE.fullmatch(row["ts"]) is not None
        for row in rows
    )
    require(valid == 647, f"ts_format_rows={valid} expected=647")
    return f"ts_format_rows={valid}"


@check("1.10")
def check_110(ctx: Context) -> str:
    rows = receipt_rows(ctx)
    timestamps = [row.get("ts") for row in rows]
    require(all(isinstance(ts, str) for ts in timestamps), "non_string_timestamp=1")
    pairs = list(zip(timestamps, timestamps[1:]))
    nondecreasing = sum(first <= last for first, last in pairs)
    require(
        len(pairs) == 646 and nondecreasing == 646,
        f"nondecreasing_pairs={nondecreasing} expected=646",
    )
    return f"nondecreasing_pairs={nondecreasing}"


@check("1.11")
def check_111(ctx: Context) -> str:
    rows = receipt_rows(ctx)
    require(bool(rows), "endpoints=empty/empty")
    first = rows[0].get("ts")
    last = rows[-1].get("ts")
    detail = f"endpoints={first}/{last}"
    require(
        first == EXPECTED_FIRST_TS and last == EXPECTED_LAST_TS,
        detail,
    )
    return detail


@check("1.12")
def check_112(_ctx: Context) -> str:
    tracked = set(git_lines("ls-files", "--", *sorted(CANONICAL_DATA)))
    missing = sorted(CANONICAL_DATA - tracked)
    require(not missing, f"canonical_data_untracked={','.join(missing)}")
    return "tracked=data/rollout_receipts.jsonl,data/queue.jsonl"


@check("2.01")
def check_201(ctx: Context) -> str:
    rows = queue_rows(ctx)
    require(len(rows) == 650, f"rows={len(rows)} expected=650")
    return f"rows={len(rows)}"


@check("2.02")
def check_202(ctx: Context) -> str:
    rows = queue_rows(ctx)
    purpose = 0
    plain = 0
    other = 0
    for row in rows:
        valid_base = (
            isinstance(row.get("repo"), str)
            and bool(row["repo"])
            and row.get("kind") in {"model", "dataset", "space"}
            and set(row) in ({"kind", "repo"}, {"kind", "repo", "purpose"})
        )
        value = row.get("purpose")
        if not valid_base or value is not None and not isinstance(value, str):
            other += 1
        elif isinstance(value, str) and value.strip():
            purpose += 1
        else:
            plain += 1
    require(
        (purpose, plain, other) == (13, 637, 0),
        f"purpose={purpose} plain={plain} other={other}",
    )
    return f"purpose={purpose} plain={plain} other={other}"


@check("2.03")
def check_203(ctx: Context) -> str:
    rows = queue_rows(ctx)
    marked = [row for row in rows if row.get("purpose") not in (None, "")]
    nonempty = sum(
        isinstance(row.get("purpose"), str) and bool(row["purpose"].strip())
        for row in marked
    )
    require(
        len(marked) == 13 and nonempty == 13,
        f"purpose_nonempty={nonempty} marked={len(marked)}",
    )
    return f"purpose_nonempty={nonempty}"


@check("2.04")
def check_204(ctx: Context) -> str:
    rows = queue_rows(ctx)
    kinds = Counter(row.get("kind") for row in rows)
    require(kinds == EXPECTED_QUEUE_KINDS, f"kinds={dict(kinds)}")
    return (
        f"dataset={kinds['dataset']} model={kinds['model']} "
        f"space={kinds['space']}"
    )


@check("2.05")
def check_205(ctx: Context) -> str:
    rows = queue_rows(ctx)
    unique = len({row.get("repo") for row in rows})
    require(unique == 647, f"unique={unique} expected=647")
    return f"unique={unique}"


@check("2.06")
def check_206(ctx: Context) -> str:
    rows = queue_rows(ctx)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("repo"))].append(row)

    duplicates = {repo: group for repo, group in grouped.items() if len(group) > 1}
    pairs = Counter(
        frozenset(row.get("kind") for row in group)
        for group in duplicates.values()
    )
    expected = Counter(
        {
            frozenset({"model", "dataset"}): 1,
            frozenset({"dataset", "space"}): 1,
            frozenset({"model", "space"}): 1,
        }
    )
    prefixed = sorted(
        f"{row.get('kind')}:{row.get('repo')}"
        for group in duplicates.values()
        for row in group
    )
    require(
        len(duplicates) == 3
        and all(len(group) == 2 for group in duplicates.values())
        and pairs == expected
        and len(prefixed) == 6,
        f"dup_table={duplicates!r}",
    )
    return (
        f"dup_table=3 prefixed={len(prefixed)} "
        "kind_pairs={model,dataset}/{dataset,space}/{model,space}"
    )


@check("3.01")
def check_301(ctx: Context) -> str:
    receipts = {row.get("repo") for row in receipt_rows(ctx)}
    queue = {row.get("repo") for row in queue_rows(ctx)}
    common = len(receipts & queue)
    require(
        common == 647 and receipts == queue,
        f"common={common} receipts={len(receipts)} queue={len(queue)}",
    )
    return f"common={common}"


@check("3.02")
def check_302(ctx: Context) -> str:
    receipts = receipt_rows(ctx)
    queue_keys = {
        (row.get("kind"), row.get("repo")) for row in queue_rows(ctx)
    }
    valid = sum(
        (row.get("kind"), row.get("repo")) in queue_keys for row in receipts
    )
    require(valid == 647, f"receipt_kind_in_queue={valid} expected=647")
    return f"receipt_kind_in_queue={valid}"


@check("4.01")
def check_401(_ctx: Context) -> str:
    tracked = git_lines("ls-files", "--", WATCH_TRACKED)
    require(
        tracked == [WATCH_TRACKED] and WATCH_PATH.is_file(),
        f"tracked={tracked!r}",
    )
    return f"tracked={WATCH_TRACKED}"


@check("4.02")
def check_402(_ctx: Context) -> str:
    require(WATCH_PATH.is_file(), "py_compile=missing_watch_file")
    with tempfile.TemporaryDirectory(prefix="pr1055-audit-") as temporary:
        target = Path(temporary) / "pr1055_watch.pyc"
        try:
            py_compile.compile(str(WATCH_PATH), cfile=str(target), doraise=True)
        except py_compile.PyCompileError as exc:
            raise CheckFailure(f"py_compile={exc.msg}") from exc
        require(target.is_file(), "py_compile=temp_output_missing")
    return "py_compile=temp_only executed=0"


@check("4.03")
def check_403(_ctx: Context) -> str:
    source = WATCH_PATH.read_text(encoding="utf-8")
    markers = [marker for marker in ("--assert-readonly", "REPORTED") if marker in source]
    require(
        len(markers) == 2,
        f"markers={','.join(markers)} missing_assert_readonly_or_REPORTED=1",
    )
    return "markers=--assert-readonly,REPORTED"


@check("4.04")
def check_404(_ctx: Context) -> str:
    source = WATCH_PATH.read_text(encoding="utf-8")
    found = [token for token in FORBIDDEN_TOKENS if token in source]
    require(not found, f"forbidden_tokens={len(found)} values={found!r}")
    return "forbidden_tokens=0"


def single_underscore_name(path: str) -> bool:
    name = PurePosixPath(path).name
    return name.startswith("_") and not name.startswith("__")


@check("5.01")
def check_501(_ctx: Context) -> str:
    tracked = [
        path for path in git_lines("ls-files") if single_underscore_name(path)
    ]
    ignored = [
        path
        for path in git_lines(
            "ls-files", "--others", "--ignored", "--exclude-standard"
        )
        if single_underscore_name(path)
    ]
    require(
        len(tracked) == 0,
        f"single-underscore_tracked={len(tracked)} "
        f"untracked_ignored={len(ignored)}",
    )
    return (
        f"single-underscore_tracked={len(tracked)} "
        f"untracked_ignored={len(ignored)}"
    )


def main() -> int:
    errors: dict[str, str] = {}
    try:
        receipts = read_jsonl(RECEIPTS_PATH)
    except Exception as exc:
        receipts = []
        errors["receipts"] = f"{type(exc).__name__}: {exc}"
    try:
        queue = read_jsonl(QUEUE_PATH)
    except Exception as exc:
        queue = []
        errors["queue"] = f"{type(exc).__name__}: {exc}"

    ctx = Context(receipts=receipts, queue=queue, errors=errors)
    passed = 0
    failed = 0

    for label, function in CHECKS:
        try:
            detail = function(ctx)
        except CheckFailure as exc:
            failed += 1
            print(f"FAIL {label} {exc}")
        except Exception as exc:
            failed += 1
            print(f"FAIL {label} {type(exc).__name__}: {exc}")
        else:
            passed += 1
            print(f"PASS {label} {detail}")

    result = "PASS" if failed == 0 else "FAIL"
    print(f"RESULT={result} pass={passed} fail={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
