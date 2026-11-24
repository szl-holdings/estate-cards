# SPDX-License-Identifier: MIT
"""Synthetic fail-closed source/readme and card-honesty checks: no network or secrets."""
import builtins
import io
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

from weaver import cards

AUDIT = {
    "generated_at": "2026-11-20T08:20:00Z",
    "hf_models": {"total": 401},
    "hf_datasets": {"total": 172},
    "hf_spaces": {"total": 78},
    "mesh": {"files": []},
}


class Response:
    status = 200
    def __init__(self, data=b"# Valid existing README\n", content_type="text/plain; charset=utf-8"):
        self.data = data
        self.headers = {"Content-Type": content_type}
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, limit):
        return self.data[:limit]


class CardTruthTest(unittest.TestCase):
    def test_model_card_uses_no_credential_and_does_not_claim_training(self):
        with patch.object(builtins, "open", side_effect=AssertionError("credential read")):
            text, assets = cards.model_card("SZLHOLDINGS/example", AUDIT)
        self.assertIn("model namespace", text)
        self.assertIn("Training / held-out evaluation:** UNKNOWN", text)
        self.assertIn("Artifact rights and weights:** NOT_REVIEWED", text)
        self.assertNotIn("trained artifact in the governed factory", text)
        self.assertTrue(assets)

    def test_metadata_cannot_smuggle_training_or_html(self):
        for value in ({"trained": "YES"}, {"signature_verified": "true"},
                      {"architecture": "<script>alert(1)</script>"},
                      {"parameters": "2B\nrights=cleared"}, []):
            with self.subTest(meta=value):
                with self.assertRaises(cards.CardReadHold):
                    cards.model_card("SZLHOLDINGS/example", AUDIT, value)

    def test_declared_metadata_is_labeled_unverified_and_html_escaped(self):
        body, _ = cards.model_card("SZLHOLDINGS/example", AUDIT,
                                   {"architecture": "Transformer & Experts"})
        self.assertIn("Declared architecture (unverified)", body)
        self.assertIn("Transformer &amp; Experts", body)
        self.assertNotIn("Transformer & Experts", body)

    def test_dataset_purpose_is_not_signed_data_provenance(self):
        body, _ = cards.dataset_card("SZLHOLDINGS/example", AUDIT, "<script>alert(1)</script>")
        self.assertIn("&lt;script&gt;", body)
        self.assertNotIn("<script>", body)
        self.assertIn("not independent dataset-lineage receipts", body)
        with self.assertRaises(cards.CardReadHold):
            cards.dataset_card("SZLHOLDINGS/example", AUDIT, "x\nunverified claim")

    def test_same_slug_in_distinct_hub_namespaces(self):
        repo_id = "SZLHOLDINGS/training-ledger-explorer"
        for kind, prefix, label in (
            ("space", "spaces/", "A Space in"),
            ("dataset", "datasets/", "A dataset repository"),
            ("model", "", "model namespace"),
        ):
            with self.subTest(kind=kind):
                body, _, _ = cards.build_card(kind, repo_id, AUDIT, "")
                self.assertIn("](https://huggingface.co/" + prefix + repo_id + ")", body)
                self.assertIn(label, body)
                if kind != "model":
                    self.assertIn("repository mapping unavailable", body)
                    self.assertNotIn("**Canonical source:**", body)
                    self.assertNotIn('src="assets/szl-card/mesh-receipts.svg"', body)

    def test_space_card_preserves_mapped_source_and_real_chart(self):
        audit = dict(AUDIT, mesh={"files": ["train-2026.json"]})
        body, assets = cards.space_card("SZLHOLDINGS/llm-router-live", audit)
        self.assertIn("**Canonical source:** https://github.com/szl-holdings/szl-router", body)
        self.assertIn("mesh-receipts.svg", assets)
        self.assertIn('src="assets/szl-card/mesh-receipts.svg"', body)

    def test_curated_readme_is_appended_not_replaced(self):
        existing = "# Curated source\n" + "Historical details.\n" * 40
        body, _, mode = cards.build_card("space", "SZLHOLDINGS/example", AUDIT, existing)
        self.assertEqual(mode, "append")
        self.assertTrue(body.startswith(existing.rstrip()))
        self.assertIn("SZL estate showcase card", body)

    def test_http_404_without_metadata_proof_stays_held(self):
        error = urllib.error.HTTPError("https://huggingface.co/test", 404, "not found", {}, None)
        with patch.object(cards, "_auth_headers", return_value={"Authorization": "Bearer synthetic"}), \
             patch.object(cards._READ_OPENER, "open", side_effect=error):
            with self.assertRaisesRegex(cards.CardReadHold, "CARD_SOURCE_UNVERIFIED"):
                cards.fetch_readme("SZLHOLDINGS/example", "model")

    def test_upstream_rejection_never_becomes_compose_permission(self):
        for code in (401, 403, 429, 503):
            error = urllib.error.HTTPError("https://huggingface.co/test", code, "error", {}, None)
            with self.subTest(code=code):
                with patch.object(cards, "_auth_headers", return_value={"Authorization": "Bearer test"}), \
                     patch.object(cards._READ_OPENER, "open", side_effect=error):
                    with self.assertRaisesRegex(cards.CardReadHold, "CARD_READ_UNAVAILABLE"):
                        cards.fetch_readme("SZLHOLDINGS/example", "model")

    def test_network_timeout_fails_closed(self):
        with patch.object(cards, "_auth_headers", return_value={"Authorization": "Bearer test"}), \
             patch.object(cards._READ_OPENER, "open", side_effect=TimeoutError("hung")):
            with self.assertRaisesRegex(cards.CardReadHold, "CARD_READ_UNAVAILABLE"):
                cards.fetch_readme("SZLHOLDINGS/example", "dataset")

    def test_source_read_is_bounded_and_exact(self):
        body = b"---\ntitle: Existing\n---\nCurated source content.\n"
        with patch.object(cards, "_auth_headers", return_value={"Authorization": "Bearer test"}), \
             patch.object(cards._READ_OPENER, "open", return_value=Response(body)):
            self.assertEqual(cards.fetch_readme("SZLHOLDINGS/example", "dataset").encode(), body)

    def test_empty_html_invalid_encoding_and_oversize_fail(self):
        cases = (
            (Response(b""), "CARD_READ_EMPTY"),
            (Response(b"<html>challenge</html>", "text/html"), "CARD_READ_CONTENT_TYPE_INVALID"),
            (Response(b"\xff\xfe"), "CARD_READ_NOT_UTF8"),
            (Response(b"a" * (cards.README_LIMIT + 1)), "CARD_READ_TOO_LARGE"),
        )
        for response, reason in cases:
            with self.subTest(reason=reason):
                with patch.object(cards, "_auth_headers", return_value={"Authorization": "Bearer test"}), \
                     patch.object(cards._READ_OPENER, "open", return_value=response):
                    with self.assertRaisesRegex(cards.CardReadHold, reason):
                        cards.fetch_readme("SZLHOLDINGS/example", "model")

    def test_bad_repo_id_fails_before_authentication(self):
        for value in ("SZLHOLDINGS/../other", "other/name", "SZLHOLDINGS/name?test", ""):
            with self.subTest(value=value):
                with patch.object(cards, "_auth_headers", side_effect=AssertionError("credential accessed")):
                    with self.assertRaisesRegex(cards.CardReadHold, "CARD_SOURCE_ID_INVALID"):
                        cards.fetch_readme(value, "model")

    def test_missing_auth_is_generic_hold(self):
        with patch.object(builtins, "open", side_effect=OSError("synthetic no auth")):
            with self.assertRaisesRegex(cards.CardReadHold, "CARD_AUTH_UNAVAILABLE"):
                cards._auth_headers()

    def test_redirect_cannot_forward_bearer_to_any_origin(self):
        request = urllib.request.Request(
            "https://huggingface.co/models/SZLHOLDINGS/example/raw/main/README.md",
            headers={"Authorization": "Bearer synthetic"},
        )
        with self.assertRaisesRegex(cards.CardReadHold, "CARD_READ_REDIRECT_REFUSED"):
            cards._NoRedirect().redirect_request(
                request, io.BytesIO(b""), 302, "Moved", {}, "https://evil.example/steal",
            )


class CardCanonicalRoutesTest(unittest.TestCase):
    """Live-observed route semantics, synthetic network-free request validation."""

    def test_model_readme_uses_canonical_route_not_false_404_models_prefix(self):
        called = []

        def fake_open(request, timeout):
            called.append(request.full_url)
            return Response(b"# Existing curated model card\n")

        with (
            patch.object(cards, "_auth_headers", return_value={"Authorization": "Bearer synthetic"}),
            patch.object(cards._READ_OPENER, "open", side_effect=fake_open),
        ):
            result = cards.fetch_readme("SZLHOLDINGS/SZL-Khipu-Yachay-Nano", "model")
        self.assertEqual(result, "# Existing curated model card\n")
        self.assertEqual(
            called,
            ["https://huggingface.co/SZLHOLDINGS/SZL-Khipu-Yachay-Nano/raw/main/README.md"],
        )

    def test_dataset_uses_specific_route_and_space_direct_read_is_denied(self):
        called = []

        def fake_open(request, timeout):
            called.append(request.full_url)
            return Response()

        with (
            patch.object(cards, "_auth_headers", return_value={"Authorization": "Bearer synthetic"}),
            patch.object(cards._READ_OPENER, "open", side_effect=fake_open),
        ):
            self.assertTrue(cards.fetch_readme("SZLHOLDINGS/example", "dataset"))
            with self.assertRaisesRegex(cards.CardReadHold, "CARD_SOURCE_ID_INVALID"):
                cards.fetch_readme("SZLHOLDINGS/example", "space")
        self.assertEqual(called, [
            "https://huggingface.co/datasets/SZLHOLDINGS/example/raw/main/README.md"
        ])


if __name__ == "__main__":
    unittest.main()
