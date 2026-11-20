"""Fail-closed public Hub source-ownership preflight for showcase README writes.

Read-only metadata only. A successful preflight is not a release approval:
the resulting immutable SHA must be used as the Hub commit parent.
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request

KINDS = {"model": "models", "dataset": "datasets", "space": "spaces"}
REPO_ID = re.compile(r"SZLHOLDINGS/[A-Za-z0-9][A-Za-z0-9._-]{0,95}\Z")
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
# Preserve source-owned Spaces even if an external writer deletes SOURCE.json.
IMMUTABLE_TARGETS = frozenset({("space", "SZLHOLDINGS/khipu-proof-loom")})
MAX_JSON = 262_144
MAX_ROOT_ENTRIES = 1_000


class Hold(RuntimeError):
    """No card write may proceed, including after metadata/API uncertainty."""


def _public_json(url: str):
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "SZL-card-source-guard/1"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            if response.status != 200:
                raise Hold("HUB_METADATA_HTTP_NOT_OK")
            payload = response.read(MAX_JSON + 1)
    except Hold:
        raise
    except Exception as exc:
        raise Hold("HUB_METADATA_UNAVAILABLE") from None
    if len(payload) > MAX_JSON:
        raise Hold("HUB_METADATA_OVERSIZE")
    try:
        return json.loads(payload)
    except (ValueError, UnicodeError):
        raise Hold("HUB_METADATA_INVALID_JSON") from None


def check(repo_id: str, kind: str, *, fetch=None) -> str:
    """Return the pinned Hub parent SHA or deny the write. Never read credentials."""
    if kind not in KINDS or not isinstance(repo_id, str) or not REPO_ID.fullmatch(repo_id):
        raise Hold("HUB_REPOSITORY_IDENTITY_INVALID")
    if (kind, repo_id) in IMMUTABLE_TARGETS:
        raise Hold("IMMUTABLE_SOURCE_OWNER_CONTROLS_README")
    fetch = _public_json if fetch is None else fetch
    base = "https://huggingface.co/api/" + KINDS[kind] + "/" + urllib.parse.quote(repo_id, safe="/")
    try:
        info = fetch(base + "/revision/HEAD?expand=sha&expand=private")
    except Hold:
        raise
    except Exception:
        raise Hold("HUB_IDENTITY_METADATA_UNAVAILABLE") from None
    if not isinstance(info, dict) or info.get("private") is not False:
        raise Hold("PUBLIC_REPOSITORY_IDENTITY_NOT_PROVED")
    parent = info.get("sha")
    if not isinstance(parent, str) or not SHA40.fullmatch(parent):
        raise Hold("HUB_PARENT_COMMIT_UNAVAILABLE")
    try:
        tree = fetch(base + "/tree/" + parent + "?recursive=false")
    except Hold:
        raise
    except Exception:
        raise Hold("HUB_TREE_METADATA_UNAVAILABLE") from None
    if not isinstance(tree, list) or not 0 < len(tree) < MAX_ROOT_ENTRIES:
        raise Hold("HUB_TREE_INCOMPLETE")
    paths = [row.get("path") if isinstance(row, dict) else None for row in tree]
    if any(not isinstance(path, str) or not path for path in paths) or len(paths) != len(set(paths)):
        raise Hold("HUB_TREE_INVALID")
    if "SOURCE.json" in paths:
        raise Hold("SOURCE_MANIFEST_GOVERNS_README")
    return parent
