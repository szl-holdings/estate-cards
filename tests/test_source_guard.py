"""No-network test fixtures for source-owned Hub cards and parent-CAS."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from weaver import cards, rollout_hf, source_guard as guard

SHA = "a" * 40
PROTECTED = "SZLHOLDINGS/khipu-proof-loom"
SAFE = "SZLHOLDINGS/frontier-console"

def fetch_ok(url):
    if "/revision/HEAD" in url:
        return {"sha": SHA, "private": False}
    if "/tree/" in url:
        return [{"path": "README.md"}, {"path": ".gitattributes"}]
    raise AssertionError("unexpected API URL")

class Response:
    status = 200
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self):
        return b'{"fixture":true}'

class SourceGuardTests(unittest.TestCase):
    def test_static_immutable_target_never_networks(self):
        with self.assertRaisesRegex(guard.Hold, "IMMUTABLE_SOURCE_OWNER"):
            guard.check(PROTECTED, "space", fetch=lambda url: self.fail("network"))

    def test_source_json_blocks_showcase_writer(self):
        def with_source(url):
            if "/revision/HEAD" in url:
                return {"sha": SHA, "private": False}
            return [{"path": ".gitattributes"}, {"path": "README.md"}, {"path": "SOURCE.json"}]
        with self.assertRaisesRegex(guard.Hold, "SOURCE_MANIFEST"):
            guard.check(SAFE, "space", fetch=with_source)

    def test_clean_metadata_binds_cas_parent(self):
        requests = []
        def record(url):
            requests.append(url)
            return fetch_ok(url)
        self.assertEqual(guard.check(SAFE, "space", fetch=record), SHA)
        self.assertEqual(len(requests), 2)
        self.assertIn("/tree/" + SHA, requests[1])

    def test_identity_and_missing_metadata_fail_closed(self):
        for repo, kind in (("other-org/evil", "space"),
                           ("SZLHOLDINGS/a/../../bad", "space"),
                           (SAFE, "mystery"),
                           ("SZLHOLDINGS/", "model")):
            with self.subTest(repo=repo, kind=kind):
                with self.assertRaises(guard.Hold):
                    guard.check(repo, kind, fetch=lambda url: self.fail("network"))
        for response in ({"sha": SHA, "private": True}, {"sha": "main", "private": False},
                         {"sha": SHA}, None):
            with self.subTest(response=response):
                with self.assertRaises(guard.Hold):
                    guard.check(SAFE, "space", fetch=lambda url: response)

    def test_missing_or_ambiguous_tree_fails_closed(self):
        for tree in ([], [{"path": "README.md"}] * 1000,
                     [{"path": "README.md"}, {"path": "README.md"}],
                     [{"bad": "entry"}], {"path": "README.md"}):
            def get(url):
                return {"sha": SHA, "private": False} if "/revision/HEAD" in url else tree
            with self.subTest(entries=len(tree)):
                with self.assertRaises(guard.Hold):
                    guard.check(SAFE, "space", fetch=get)

    def test_provider_fetch_failure_fails_closed(self):
        with self.assertRaisesRegex(guard.Hold, "UNAVAILABLE"):
            guard.check(SAFE, "space", fetch=lambda url: 1/0)

    def test_paginated_tree_refuses_missing_manifest_in_first_page(self):
        class PaginatedResponse(Response):
            headers = {"Link": '<https://huggingface.co/api/spaces/x/tree/main?cursor=next>; rel="next"'}
            def read(self, count):
                return b'[{"path":"README.md"}]'
        with patch.object(guard.urllib.request, "urlopen", return_value=PaginatedResponse()):
            with self.assertRaisesRegex(guard.Hold, "PAGINATION_UNVERIFIED"):
                guard._public_json("https://huggingface.co/api/spaces/SZLHOLDINGS/x/tree/main")

    def test_ndjson_has_exact_parent_commit(self):
        observed = []
        def urlopen(request, timeout):
            observed.append(request)
            return Response()
        with patch.object(rollout_hf, "_write_token", return_value="TEST_FIXTURE_ONLY"), \
             patch.object(rollout_hf.urllib.request, "urlopen", side_effect=urlopen):
            code, _ = rollout_hf.ndjson_commit(SAFE, "space", [("README.md", "fixture")], SHA)
        self.assertEqual(code, 200)
        self.assertEqual(len(observed), 1)
        self.assertEqual(observed[0].get_method(), "POST")
        header = json.loads(observed[0].data.decode().splitlines()[0])
        self.assertEqual(header["value"]["parentCommit"], SHA)

    def test_public_readme_uses_immutable_revision_without_auth(self):
        requests = []
        class ReadmeResponse:
            status = 200
            headers = {"Content-Type": "text/plain; charset=utf-8"}
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self, count):
                return b"# Public README"
        def fake_urlopen(request, timeout):
            requests.append(request)
            return ReadmeResponse()
        with patch.object(cards.urllib.request, "urlopen", side_effect=fake_urlopen):
            observed = cards.fetch_readme(SAFE, "space", parent_revision=SHA)
        self.assertEqual(observed, "# Public README")
        self.assertEqual(len(requests), 1)
        self.assertIn("/raw/" + SHA + "/README.md", requests[0].full_url)
        self.assertNotIn("authorization", dict(requests[0].header_items()))

    def test_public_model_card_uses_canonical_root_url(self):
        class ReadmeResponse:
            status = 200
            headers = {"Content-Type": "text/plain; charset=utf-8"}
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self, count):
                return b"# Model card"
        requests = []
        def fake_urlopen(request, timeout):
            requests.append(request)
            return ReadmeResponse()
        with patch.object(cards.urllib.request, "urlopen", side_effect=fake_urlopen):
            self.assertEqual(
                cards.fetch_readme("SZLHOLDINGS/WILLAY", "model", parent_revision=SHA),
                "# Model card",
            )
        self.assertEqual(
            requests[0].full_url,
            "https://huggingface.co/SZLHOLDINGS/WILLAY/raw/" + SHA + "/README.md",
        )
        self.assertNotIn("authorization", dict(requests[0].header_items()))

    def test_html_200_does_not_become_curated_readme(self):
        class HtmlResponse:
            status = 200
            headers = {"Content-Type": "text/html; charset=utf-8"}
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self, count):
                return b"<html>proxy error</html>"
        with patch.object(cards.urllib.request, "urlopen", return_value=HtmlResponse()):
            with self.assertRaisesRegex(guard.Hold, "README_NON_TEXT"):
                cards.fetch_readme(SAFE, "space", parent_revision=SHA)

    def test_rate_limit_and_upstream_http_errors_hold_without_fallback(self):
        import urllib.error
        for status in (401, 403, 429, 500, 503):
            with self.subTest(http=status):
                failure = urllib.error.HTTPError(
                    "https://huggingface.co/", status, "fixture", {}, None
                )
                with patch.object(cards.urllib.request, "urlopen", side_effect=failure):
                    with self.assertRaisesRegex(guard.Hold, "README_HTTP_UNAVAILABLE"):
                        cards.fetch_readme(SAFE, "space", parent_revision=SHA)

    def test_readme_network_failure_fails_closed(self):
        with patch.object(cards.urllib.request, "urlopen", side_effect=TimeoutError("offline")):
            with self.assertRaisesRegex(guard.Hold, "README_TRANSPORT_UNAVAILABLE"):
                cards.fetch_readme(SAFE, "space", parent_revision=SHA)

    def test_readme_missing_fails_closed_instead_of_overwriting(self):
        import urllib.error
        missing = urllib.error.HTTPError("https://example.invalid", 404, "missing", {}, None)
        with patch.object(cards.urllib.request, "urlopen", side_effect=missing):
            with self.assertRaisesRegex(guard.Hold, "README_HTTP_UNAVAILABLE"):
                cards.fetch_readme(SAFE, "space", parent_revision=SHA)

    def test_bad_readme_revision_never_attempts_network(self):
        with patch.object(cards.urllib.request, "urlopen", side_effect=AssertionError("network")):
            with self.assertRaisesRegex(guard.Hold, "README_SOURCE_IDENTITY_INVALID"):
                cards.fetch_readme(SAFE, "space", parent_revision="main")

    def test_bad_parent_never_reads_token_or_posts(self):
        with patch.object(rollout_hf, "_write_token", side_effect=AssertionError("secret")), \
             patch.object(rollout_hf.urllib.request, "urlopen", side_effect=AssertionError("network")):
            with self.assertRaisesRegex(guard.Hold, "PARENT_UNAVAILABLE"):
                rollout_hf.ndjson_commit(SAFE, "space", [("README.md", "x")], "main")

    def test_immutable_queue_item_is_hold_without_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data").mkdir()
            (root/"data"/"audit-latest.json").write_text("{}")
            (root/"queue.jsonl").write_text(json.dumps({"kind":"space","repo":PROTECTED})+"\n")
            overrides = {"ROOT":str(root), "Q":str(root/"queue.jsonl"),
                         "RCPT":str(root/"rollout_receipts.jsonl"),
                         "STATE":str(root/"rollout_state.json"), "STOP":str(root/"STOP")}
            with patch.multiple(rollout_hf, **overrides), \
                 patch.object(rollout_hf, "ndjson_commit", side_effect=AssertionError("POST")), \
                 patch.object(rollout_hf.cardbox, "fetch_readme", side_effect=AssertionError("fetch")):
                rollout_hf.main()
            receipt=json.loads((root/"rollout_receipts.jsonl").read_text().splitlines()[0])
            self.assertEqual(receipt["admission"], "HOLD")
            self.assertFalse((root/"rollout_state.json").exists())

if __name__ == "__main__":
    unittest.main()
