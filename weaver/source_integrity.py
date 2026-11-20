"""Fail-closed README mutation admission for independently source-bound Hub assets.

A successful README write must never silently invalidate an immutable
source-to-deployment manifest. This module is read-only and never sees model
output or issues commits. Unknown upstream state is a HOLD, not an absence.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from typing import Any

REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
KIND_PLURAL = {"model": "models", "dataset": "datasets", "space": "spaces"}
MAX_MANIFEST_BYTES = 32768
CODES = frozenset({
    "SOURCE_REPO_INVALID",
    "SOURCE_REPO_TYPE_INVALID",
    "SOURCE_MANIFEST_PRESENT",
    "SOURCE_MANIFEST_TOO_LARGE",
    "SOURCE_MANIFEST_UNREADABLE",
    "SOURCE_MANIFEST_UNKNOWN",
    "SOURCE_GUARD_HTTP_UNEXPECTED",
    "SOURCE_GUARD_PROVIDER_UNAVAILABLE",
    "SOURCE_GUARD_REDIRECT_REFUSED",
    "SOURCE_HEAD_UNAVAILABLE",
    "SOURCE_HEAD_INVALID",
    "SOURCE_HEAD_TOO_LARGE",
})


class SourceIntegrityHold(ValueError):
    """Fixed refusal reason; never include credentials or remote body."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, hdrs, newurl):
        raise SourceIntegrityHold("SOURCE_GUARD_REDIRECT_REFUSED")


def assert_readme_unbound(
    repo_id: str,
    kind: str,
    *,
    headers: Mapping[str, str] | None = None,
    opener: Any = None,
) -> str:
    """Permit README mutation only after a genuine 404 for SOURCE.json.

    Any existing SOURCE.json, even an unrecognized version, is potentially an
    immutable source-owner agreement. A showcase renderer is not that owner
    and must not silently rewrite its README. HTTP 401/403/429/5xx, invalid
    JSON, redirects, timeouts and ambiguous responses all fail closed.
    """
    if type(repo_id) is not str or REPO.fullmatch(repo_id) is None:
        raise SourceIntegrityHold("SOURCE_REPO_INVALID")
    if type(kind) is not str or kind not in KIND_PLURAL:
        raise SourceIntegrityHold("SOURCE_REPO_TYPE_INVALID")
    if headers is not None and not isinstance(headers, Mapping):
        raise SourceIntegrityHold("SOURCE_GUARD_PROVIDER_UNAVAILABLE")

    # The only remote host is the fixed Hub origin. Never forward credentials
    # to a redirected or model-suggested URL.
    url = ("https://huggingface.co/" + KIND_PLURAL[kind] + "/"
           + urllib.parse.quote(repo_id, safe="/")
           + "/resolve/main/SOURCE.json")
    safe_headers = {"User-Agent": "szl-estate-cards-source-integrity/1"}
    if headers:
        auth = headers.get("Authorization")
        if type(auth) is str:
            safe_headers["Authorization"] = auth
    request = urllib.request.Request(url, headers=safe_headers, method="GET")
    client = opener if opener is not None else urllib.request.build_opener(
        urllib.request.ProxyHandler({}), _NoRedirect(),
    )
    try:
        with client.open(request, timeout=15) as response:
            if response.status != 200:
                raise SourceIntegrityHold("SOURCE_GUARD_HTTP_UNEXPECTED")
            raw = response.read(MAX_MANIFEST_BYTES + 1)
    except SourceIntegrityHold:
        raise
    except urllib.error.HTTPError as exc:
        # Real 404 is the only sufficiently specific absence evidence.
        if exc.code == 404:
            return "SOURCE_MANIFEST_NOT_FOUND"
        raise SourceIntegrityHold("SOURCE_GUARD_PROVIDER_UNAVAILABLE") from None
    except (OSError, ValueError, TimeoutError):
        raise SourceIntegrityHold("SOURCE_GUARD_PROVIDER_UNAVAILABLE") from None

    if len(raw) > MAX_MANIFEST_BYTES:
        raise SourceIntegrityHold("SOURCE_MANIFEST_TOO_LARGE")
    try:
        document = json.loads(raw)
    except (UnicodeError, ValueError, TypeError):
        raise SourceIntegrityHold("SOURCE_MANIFEST_UNREADABLE") from None
    if not isinstance(document, dict):
        raise SourceIntegrityHold("SOURCE_MANIFEST_UNKNOWN")
    # Even if a SOURCE.json is a different schema, the showcase writer is not
    # entitled to overwrite it. Do NOT interpret an unknown owner as unowned.
    raise SourceIntegrityHold("SOURCE_MANIFEST_PRESENT")


def observed_head_sha(
    repo_id: str,
    kind: str,
    *,
    headers: Mapping[str, str] | None = None,
    opener: Any = None,
) -> str:
    """Read current HF Git HEAD for a parent-commit compare-and-swap.

    A metadata lookup is not a lease; the Hub must check the same SHA
    in the subsequent commit's parentCommit field. A stale or ambiguous
    lookup is a HOLD rather than permission to overwrite another writer.
    """
    if type(repo_id) is not str or REPO.fullmatch(repo_id) is None:
        raise SourceIntegrityHold("SOURCE_REPO_INVALID")
    if type(kind) is not str or kind not in KIND_PLURAL:
        raise SourceIntegrityHold("SOURCE_REPO_TYPE_INVALID")
    url = ("https://huggingface.co/api/" + KIND_PLURAL[kind] + "/"
           + urllib.parse.quote(repo_id, safe="/"))
    safe_headers = {"User-Agent": "szl-estate-cards-source-integrity/1"}
    if headers:
        auth = headers.get("Authorization")
        if type(auth) is str:
            safe_headers["Authorization"] = auth
    req = urllib.request.Request(url, headers=safe_headers, method="GET")
    client = opener if opener is not None else urllib.request.build_opener(
        urllib.request.ProxyHandler({}), _NoRedirect(),
    )
    try:
        with client.open(req, timeout=15) as resp:
            if resp.status != 200:
                raise SourceIntegrityHold("SOURCE_HEAD_UNAVAILABLE")
            raw = resp.read(1_000_001)
    except SourceIntegrityHold:
        raise
    except (OSError, ValueError):
        raise SourceIntegrityHold("SOURCE_HEAD_UNAVAILABLE") from None
    if len(raw) > 1_000_000:
        raise SourceIntegrityHold("SOURCE_HEAD_TOO_LARGE")
    try:
        info = json.loads(raw)
    except (UnicodeError, ValueError, TypeError):
        raise SourceIntegrityHold("SOURCE_HEAD_INVALID") from None
    head = info.get("sha") if isinstance(info, dict) else None
    if type(head) is not str or re.fullmatch(r"[0-9a-f]{40}", head) is None:
        raise SourceIntegrityHold("SOURCE_HEAD_INVALID")
    return head
