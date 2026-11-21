# SPDX-License-Identifier: MIT
"""Fail-closed source-only tests. No real Hub calls, secrets or deployments."""
import json
import os
import pathlib
import tempfile
import unittest
from unittest.mock import patch

from weaver import cards, rollout_hf

class RolloutGuardTests(unittest.TestCase):
    def fake_queue(self, items):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = pathlib.Path(td.name)
        (root / "data").mkdir()
        (root / "data" / "audit-latest.json").write_text("{}", encoding="utf-8")
        queue = root / "queue.jsonl"
        queue.write_text("".join(json.dumps(item)+"\n" for item in items), encoding="utf-8")
        for name, value in {
            "ROOT": str(root), "Q": str(queue),
            "RCPT": str(root / "rollout_receipts.jsonl"),
            "STATE": str(root / "rollout_state.json"),
            "STOP": str(root / "STOP"),
        }.items():
            p=patch.object(rollout_hf, name, value)
            p.start()
            self.addCleanup(p.stop)
        return root

    def test_import_only_uses_explicit_environment(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(cards._read_headers(), {})
            with self.assertRaisesRegex(RuntimeError, "EXPLICIT_CARD_PUBLISH_TOKEN_REQUIRED"):
                rollout_hf._publisher_token()

    def test_space_commit_denied_before_network(self):
        with patch.dict(os.environ, {"SZL_HF_CARD_PUBLISH_TOKEN": "fake"}, clear=True):
            with patch.object(rollout_hf.urllib.request, "urlopen", side_effect=AssertionError("network")):
                status, reason = rollout_hf.ndjson_commit(
                    "SZLHOLDINGS/khipu-proof-loom", "space", [("README.md", "changed")], approved=True)
        self.assertEqual((status, reason), (403, "SOURCE_OWNED_SPACE_PUBLISHER_REQUIRED"))

    def test_model_direct_commit_without_admission_denied(self):
        with patch.object(rollout_hf.urllib.request, "urlopen", side_effect=AssertionError("network")):
            code, reason=rollout_hf.ndjson_commit("SZLHOLDINGS/m","model",[],approved=False)
        self.assertEqual((code,reason),(403,"EXPLICIT_OWNER_CARD_ADMISSION_REQUIRED"))
        # A caller cannot impersonate operator approval with approved=True.
        with patch.dict(os.environ, {}, clear=True):
            code, reason = rollout_hf.ndjson_commit("SZLHOLDINGS/m", "model", [], approved=True)
        self.assertEqual((code,reason),(403,"EXPLICIT_OWNER_CARD_ADMISSION_REQUIRED"))

    def test_default_dry_run_no_fetch_or_commit(self):
        root=self.fake_queue([
            {"kind":"space","repo":"SZLHOLDINGS/khipu-proof-loom"},
            {"kind":"model","repo":"SZLHOLDINGS/test-model"},
            {"kind":"dataset","repo":"SZLHOLDINGS/test-data"},
        ])
        with patch.dict(os.environ, {}, clear=True), \
             patch.object(rollout_hf.cardbox,"fetch_readme",side_effect=AssertionError("fetch")), \
             patch.object(rollout_hf,"ndjson_commit",side_effect=AssertionError("commit")):
            rollout_hf.main([])
        decisions=[json.loads(l)["decision"] for l in (root/"rollout_receipts.jsonl").read_text().splitlines()]
        self.assertEqual(decisions,[
            "SOURCE_OWNED_SPACE_PUBLISHER_REQUIRED",
            "DRY_RUN_REVIEW_REQUIRED", "DRY_RUN_REVIEW_REQUIRED"])
        self.assertFalse((root/"rollout_state.json").exists())

    def test_apply_without_token_does_not_touch_space_or_network(self):
        root=self.fake_queue([
            {"kind":"space","repo":"SZLHOLDINGS/khipu-proof-loom"},
            {"kind":"model","repo":"SZLHOLDINGS/test-model"},
        ])
        with patch.dict(os.environ, {}, clear=True), \
             patch.object(rollout_hf.cardbox,"fetch_readme",side_effect=AssertionError("fetch")), \
             patch.object(rollout_hf,"ndjson_commit",side_effect=AssertionError("commit")):
            rollout_hf.main(["--apply", "--repo", "SZLHOLDINGS/test-model"])
        decisions=[json.loads(l)["decision"] for l in (root/"rollout_receipts.jsonl").read_text().splitlines()]
        self.assertEqual(decisions,["EXPLICIT_CARD_PUBLISH_TOKEN_REQUIRED"])

    def test_invalid_repo_and_kind(self):
        root=self.fake_queue([
            {"kind":"model","repo":"SZLHOLDINGS/../escape"},
            {"kind":"other","repo":"SZLHOLDINGS/test"},
        ])
        with patch.object(rollout_hf,"ndjson_commit",side_effect=AssertionError("commit")):
            rollout_hf.main([])
        decisions=[json.loads(l)["decision"] for l in (root/"rollout_receipts.jsonl").read_text().splitlines()]
        self.assertEqual(decisions,["INVALID_REPOSITORY","INVALID_REPOSITORY_KIND"])

    def test_unrecognized_override_rejected(self):
        with self.assertRaisesRegex(ValueError,"USAGE"):
            rollout_hf.main(["--override-space"])

    def test_model_apply_synthetic_writer_only(self):
        root=self.fake_queue([{"kind":"model","repo":"SZLHOLDINGS/test-model"}])
        with patch.dict(os.environ, {"SZL_HF_CARD_PUBLISH_TOKEN":"test-only",
                                     "SZL_HF_CARD_APPROVED_TARGET":"model:SZLHOLDINGS/test-model"}, clear=True), \
             patch.object(rollout_hf.cardbox,"fetch_readme",return_value="# curated"), \
             patch.object(rollout_hf.cardbox,"build_card",return_value=("card",{},"append")), \
             patch.object(rollout_hf,"ndjson_commit",return_value=(200,"")) as writer, \
             patch.object(rollout_hf.time,"sleep",return_value=None):
            rollout_hf.main(["--apply", "--repo", "SZLHOLDINGS/test-model"])
        writer.assert_called_once_with("SZLHOLDINGS/test-model","model",
            [("README.md","card")],approved=True)
        self.assertEqual(json.loads((root/"rollout_state.json").read_text())["done"],["SZLHOLDINGS/test-model"])

    def test_apply_requires_one_exact_repo_selector(self):
        for args in (["--apply"], ["--apply", "--repo", "SZLHOLDINGS/../escape"],
                     ["--apply", "--repo", "SZLHOLDINGS/m", "--all"]):
            with self.subTest(args=args), self.assertRaisesRegex(ValueError, "USAGE"):
                rollout_hf.main(args)

    def test_apply_requires_exact_operator_target_even_with_token(self):
        root = self.fake_queue([{"kind":"model","repo":"SZLHOLDINGS/test-model"}])
        with patch.dict(os.environ, {"SZL_HF_CARD_PUBLISH_TOKEN":"test-only"}, clear=True), \
             patch.object(rollout_hf.cardbox,"fetch_readme",side_effect=AssertionError("fetch")), \
             patch.object(rollout_hf,"ndjson_commit",side_effect=AssertionError("write")):
            rollout_hf.main(["--apply","--repo","SZLHOLDINGS/test-model"])
        decisions=[json.loads(line)["decision"] for line in
                   (root/"rollout_receipts.jsonl").read_text().splitlines()]
        self.assertEqual(decisions, ["EXPLICIT_OWNER_CARD_ADMISSION_REQUIRED"])
        self.assertFalse((root/"rollout_state.json").exists())

    def test_apply_touches_only_exact_approved_queue_row(self):
        root=self.fake_queue([
            {"kind":"dataset","repo":"SZLHOLDINGS/other-data"},
            {"kind":"model","repo":"SZLHOLDINGS/test-model"},
            {"kind":"model","repo":"SZLHOLDINGS/other-model"},
        ])
        env={"SZL_HF_CARD_PUBLISH_TOKEN":"test-only",
             "SZL_HF_CARD_APPROVED_TARGET":"model:SZLHOLDINGS/test-model"}
        with patch.dict(os.environ,env,clear=True), \
             patch.object(rollout_hf.cardbox,"fetch_readme",return_value="# curated") as fetch, \
             patch.object(rollout_hf.cardbox,"build_card",return_value=("card",{},"append")), \
             patch.object(rollout_hf,"ndjson_commit",return_value=(200,"")) as writer, \
             patch.object(rollout_hf.time,"sleep",return_value=None):
            rollout_hf.main(["--apply","--repo","SZLHOLDINGS/test-model"])
        fetch.assert_called_once_with("SZLHOLDINGS/test-model","model")
        writer.assert_called_once_with("SZLHOLDINGS/test-model","model",
                                       [("README.md","card")],approved=True)
        self.assertEqual(json.loads((root/"rollout_state.json").read_text())["done"],
                         ["SZLHOLDINGS/test-model"])

    def test_duplicate_approval_target_refuses_all_network(self):
        self.fake_queue([
            {"kind":"model","repo":"SZLHOLDINGS/test-model"},
            {"kind":"model","repo":"SZLHOLDINGS/test-model"},
        ])
        env={"SZL_HF_CARD_PUBLISH_TOKEN":"test-only",
             "SZL_HF_CARD_APPROVED_TARGET":"model:SZLHOLDINGS/test-model"}
        with patch.dict(os.environ,env,clear=True), \
             patch.object(rollout_hf.cardbox,"fetch_readme",side_effect=AssertionError("fetch")):
            with self.assertRaisesRegex(ValueError, "EXPLICIT_APPROVED_REPOSITORY"):
                rollout_hf.main(["--apply","--repo","SZLHOLDINGS/test-model"])

    def test_curated_card_refresh_is_idempotent_and_preserves_license(self):
        audit = {
            "hf_models": {"total": 401}, "hf_datasets": {"total": 172},
            "hf_spaces": {"total": 78}, "generated_at": "2026-11-20T08:00:00Z",
            "mesh": {"files": []},
        }
        curated = "---\nlicense: apache-2.0\n---\n\n# Model\n" + ("Public research.\n" * 60)
        first, _assets, mode = cards.build_card(
            "model", "SZLHOLDINGS/test-model", audit, curated)
        self.assertEqual(mode, "append")
        second, _assets, mode = cards.build_card(
            "model", "SZLHOLDINGS/test-model", audit, first)
        self.assertEqual(mode, "replace-marked")
        self.assertTrue(second.startswith(curated.rstrip()))
        self.assertEqual(second.count("## SZL estate showcase card"), 1)
        self.assertEqual(second.count(cards.CARD_MARK), 1)
        self.assertIn("license: apache-2.0", second)
        self.assertIn("weight and evaluation qualification NOT VERIFIED", second)
        self.assertNotIn("trained artifact in the governed factory", second)
        third, _assets, mode = cards.build_card(
            "model", "SZLHOLDINGS/test-model", audit, second)
        self.assertEqual(mode, "replace-marked")
        self.assertEqual(third.count("## SZL estate showcase card"), 1)

    def test_malformed_card_marker_fails_closed(self):
        audit = {
            "hf_models": {"total": 1}, "hf_datasets": {"total": 1},
            "hf_spaces": {"total": 1}, "generated_at": "2026-11-20T00:00:00Z",
            "mesh": {"files": []},
        }
        with self.assertRaisesRegex(ValueError, "SOURCE_CARD_SECTION_UNBOUND"):
            cards.build_card(
                "dataset", "SZLHOLDINGS/test-data", audit,
                "# Curated\n" + cards.CARD_MARK + " truncated")


    def test_unavailable_readme_cannot_overwrite_a_model_card(self):
        root = self.fake_queue([{"kind":"model","repo":"SZLHOLDINGS/test-model"}])
        with patch.dict(os.environ, {"SZL_HF_CARD_PUBLISH_TOKEN":"test-only",
                                     "SZL_HF_CARD_APPROVED_TARGET":"model:SZLHOLDINGS/test-model"}, clear=True), \
             patch.object(rollout_hf.cardbox, "fetch_readme", return_value=None), \
             patch.object(rollout_hf, "ndjson_commit", side_effect=AssertionError("commit")), \
             patch.object(rollout_hf.time, "sleep", return_value=None):
            rollout_hf.main(["--apply", "--repo", "SZLHOLDINGS/test-model"])
        rows=[json.loads(l) for l in (root/"rollout_receipts.jsonl").read_text().splitlines()]
        self.assertEqual(len(rows),1)
        self.assertIn("README_READ_UNAVAILABLE_FAIL_CLOSED",rows[0].get("err",""))
        self.assertFalse((root/"rollout_state.json").exists())


if __name__=="__main__":
    unittest.main()
