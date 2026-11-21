"""Build a short bounded GitHub org profile marker and a detailed dated evidence page.

No provider calls, credentials, deployment or training. The 430-word front-door
contract belongs to .github; this generator never increases that limit.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UTC_STAMP = re.compile(r"^20[0-9]{2}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")


def _count(source: dict, *path: str) -> int:
    value = source
    for key in path:
        if not isinstance(value, dict) or key not in value:
            raise ValueError("missing required measured count")
        value = value[key]
    if type(value) is not int or not 0 <= value <= 1_000_000:
        raise ValueError("invalid measured count")
    return value


def render(audit: dict) -> tuple[str, str]:
    """Return (bounded index block, detailed evidence page) from one audit."""
    if not isinstance(audit, dict):
        raise ValueError("invalid audit")
    stamp = audit.get("generated_at")
    if not isinstance(stamp, str) or UTC_STAMP.fullmatch(stamp) is None:
        raise ValueError("invalid captured timestamp")
    gh = _count(audit, "gh", "total")
    models = _count(audit, "hf_models", "total")
    datasets = _count(audit, "hf_datasets", "total")
    spaces = _count(audit, "hf_spaces", "total")
    mesh = audit.get("mesh")
    files = mesh.get("files") if isinstance(mesh, dict) else None
    if not isinstance(files, list) or len(files) > 1_000_000:
        raise ValueError("invalid receipt list")
    stages = (audit.get("space_runtime") or {}).get("stages")
    if not isinstance(stages, dict):
        runtime = "Runtime stage census unavailable; no RUNNING claim."
    elif len(stages) != spaces:
        runtime = "Runtime stage coverage incomplete; no fleet-wide RUNNING claim."
    else:
        running = sum(state == "RUNNING" for state in stages.values())
        runtime = f"{running}/{spaces} Spaces labeled RUNNING at capture; this is not route or release proof."
    summary = (
        f"<!-- szl:estate-cards:v1 generated {stamp} -->\n\n"
        "## Snapshot\n\n"
        "[Census and limitations](ESTATE_AT_A_GLANCE.md).\n\n"
        "<!-- /szl:estate-cards:v1 -->"
    )
    if len(summary.split()) > 35:
        raise ValueError("index section exceeded allocated word budget")
    detail = (
        f"# SZL estate at a glance — measured {stamp}\n\n"
        "Dated observations, not training completions, quality, payment settlements, "
        "or production promotion. Counts and stages may have changed. "
        "[Audit source](https://github.com/szl-holdings/estate-cards/blob/main/data/audit-latest.json) "
        "is a moving reference; retain the captured input and digest with the PR.\n\n"
        f"- GitHub repositories: **{gh}**.\n"
        f"- Hugging Face models: **{models}**, datasets: **{datasets}**, Spaces: **{spaces}**.\n"
        f"- Receipt files in the observed mesh listing: **{len(files)}**.\n"
        f"- Runtime: {runtime}\n\n"
        "![Fleet](assets/graphs/org-fleet.svg)\n\n"
        "![Space stages](assets/graphs/org-spaces.svg)\n\n"
        "![Mesh families](assets/graphs/org-mesh.svg)\n\n"
        "[Rollout receipts](https://github.com/szl-holdings/estate-cards/blob/main/rollout_receipts.jsonl) "
        "record attempts, not guaranteed successful publication.\n"
    )
    return summary, detail


def main() -> None:
    audit = json.loads((ROOT / "data" / "audit-latest.json").read_text(encoding="utf-8"))
    summary, detail = render(audit)
    (ROOT / "data" / "profile_section.md").write_text(summary + "\n", encoding="utf-8")
    (ROOT / "data" / "profile_details.md").write_text(detail, encoding="utf-8")
    print("PROFILE_ARTIFACTS_WRITTEN; review GitHub 430-word budget and historical marker before publishing")


if __name__ == "__main__":
    main()
