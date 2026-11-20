"""Offline adversarial tests for the estate-cards source-manifest write boundary."""
from __future__ import annotations

import builtins
import io
import json
import pathlib
import sys
import unittest
import urllib.error
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from weaver.source_integrity import (
    MAX_MANIFEST_BYTES,
    SourceIntegrityHold,
    _NoRedirect,
    assert_readme_unbound,
    observed_head_sha,
)

REPO = "SZLHOLDINGS/khipu-proof-loom"
MANIFEST = {
    "schema": "szl.khipu.proof-loom-publication/v1",
    "source_repository": "szl-holdings/szl-khipu",
    "source_commit": "a" * 40,
    "files": [{"source": "spaces/proof-loom/README.md", "dest": "README.md",
               "size": 123, "sha256": "b" * 64}],
}


class Response:
    status = 200

    def __init__(self, raw=b"{}", status=200):
        self.raw, self.status = raw, status

    def read(self, count=-1):
        return self.raw if count < 0 else self.raw[:count]

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class FakeOpener:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def open(self, req, timeout):
        self.calls.append((req, timeout))
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def http_error(code):
    return urllib.error.HTTPError(
        "https://huggingface.co/spaces/SZLHOLDINGS/khipu-proof-loom/resolve/main/SOURCE.json",
        code, "fixture", {}, None,
    )


class SourceIntegrityTests(unittest.TestCase):
    def test_404_only_allows_unbound_readme_edit(self):
        opener = FakeOpener(http_error(404))
        self.assertEqual(assert_readme_unbound(REPO, "space", opener=opener),
                         "SOURCE_MANIFEST_NOT_FOUND")
        self.assertEqual(len(opener.calls), 1)
        req, timeout = opener.calls[0]
        self.assertEqual(req.get_method(), "GET")
        self.assertEqual(timeout, 15)
        self.assertEqual(req.full_url,
                         "https://huggingface.co/spaces/SZLHOLDINGS/"
                         "khipu-proof-loom/resolve/main/SOURCE.json")

    def test_actual_proofloom_manifest_refuses_readme_modification(self):
        with self.assertRaisesRegex(SourceIntegrityHold,
                                    "SOURCE_MANIFEST_PRESENT"):
            assert_readme_unbound(
                REPO, "space",
                opener=FakeOpener(Response(json.dumps(MANIFEST).encode())),
            )

    def test_unknown_schema_cannot_grant_ownership(self):
        with self.assertRaisesRegex(SourceIntegrityHold,
                                    "SOURCE_MANIFEST_PRESENT"):
            assert_readme_unbound(REPO, "space",
                                  opener=FakeOpener(Response(b'{"other":"schema"}')))

    def test_missing_corrupt_or_oversized_manifest_holds(self):
        for raw in (b"", b"{", b'["not-object"]', b"x" * (MAX_MANIFEST_BYTES + 1)):
            with self.subTest(size=len(raw)), self.assertRaises(SourceIntegrityHold):
                assert_readme_unbound(REPO, "space",
                                      opener=FakeOpener(Response(raw)))

    def test_401_403_429_and_5xx_are_not_absence(self):
        for status in (401, 403, 409, 429, 500, 503):
            with (
                self.subTest(code=status),
                self.assertRaisesRegex(
                    SourceIntegrityHold, "SOURCE_GUARD_PROVIDER_UNAVAILABLE"
                ),
            ):
                assert_readme_unbound(
                    REPO, "space", opener=FakeOpener(http_error(status))
                )

    def test_timeout_and_unexpected_response_hold(self):
        with self.assertRaisesRegex(SourceIntegrityHold,
                                    "SOURCE_GUARD_PROVIDER_UNAVAILABLE"):
            assert_readme_unbound(REPO, "space", opener=FakeOpener(TimeoutError()))
        with self.assertRaisesRegex(SourceIntegrityHold,
                                    "SOURCE_GUARD_HTTP_UNEXPECTED"):
            assert_readme_unbound(REPO, "space",
                                  opener=FakeOpener(Response(status=206)))

    def test_redirect_refused(self):
        with self.assertRaisesRegex(SourceIntegrityHold,
                                    "SOURCE_GUARD_REDIRECT_REFUSED"):
            _NoRedirect().redirect_request(None, None, 302, "Location",
                                          {}, "https://evil.example/redirect")

    def test_invalid_repo_and_kind_refused(self):
        for repo, kind, code in (
            ("SZLHOLDINGS/../../wrong", "space", "SOURCE_REPO_INVALID"),
            ("SZLHOLDINGS/with space", "space", "SOURCE_REPO_INVALID"),
            (REPO, "spaces", "SOURCE_REPO_TYPE_INVALID"),
        ):
            with (
                self.subTest(repo=repo, kind=kind),
                self.assertRaisesRegex(SourceIntegrityHold, code),
            ):
                assert_readme_unbound(
                    repo, kind, opener=FakeOpener(http_error(404))
                )

    def test_auth_stays_on_pinned_origin_only(self):
        opener = FakeOpener(http_error(404))
        assert_readme_unbound(
            REPO, "space", headers={"Authorization": "Bearer DUMMY_TEST_ONLY"},
            opener=opener,
        )
        req, _ = opener.calls[0]
        self.assertEqual(req.get_header("Authorization"),
                         "Bearer DUMMY_TEST_ONLY")
        self.assertEqual(req.host, "huggingface.co")

    def test_actual_commit_boundary_checks_before_provider_post(self):
        real_open = builtins.open

        def safe_open(file, *args, **kwargs):
            if str(file).replace("\\", "/").endswith(
                ".cache/huggingface/token"
            ):
                return io.StringIO("DUMMY_TEST_ONLY")
            return real_open(file, *args, **kwargs)

        with mock.patch("builtins.open", side_effect=safe_open):
            from weaver import rollout_hf
        with (
            mock.patch.object(
                rollout_hf.source_integrity, "assert_readme_unbound",
                side_effect=SourceIntegrityHold("SOURCE_MANIFEST_PRESENT"),
            ) as protect,
            mock.patch.object(
                rollout_hf.urllib.request, "urlopen",
                side_effect=AssertionError("NO_COMMIT_ALLOWED"),
            ) as network,self.assertRaisesRegex(SourceIntegrityHold,
                                    "SOURCE_MANIFEST_PRESENT")
        ):
            rollout_hf.ndjson_commit(
                REPO, "space", [("README.md", "malicious append")],
            )
        protect.assert_called_once()
        network.assert_not_called()


    def test_readme_fetch_cannot_overwrite_on_transient_errors(self):
        real_open = builtins.open

        def safe_open(file, *args, **kwargs):
            if str(file).replace("\\", "/").endswith(
                ".cache/huggingface/token"
            ):
                return io.StringIO("DUMMY_TEST_ONLY")
            return real_open(file, *args, **kwargs)

        with mock.patch("builtins.open", side_effect=safe_open):
            from weaver import cards

        for code in (401, 403, 429, 503):
            with self.subTest(http_status=code), mock.patch.object(
                cards.urllib.request, "build_opener",
                return_value=FakeOpener(http_error(code)),
            ), self.assertRaisesRegex(
                SourceIntegrityHold, "README_PROVIDER_UNAVAILABLE"
            ):
                cards.fetch_readme(REPO, "space")

    def test_readme_fetch_404_and_200_only_are_distinct(self):
        real_open = builtins.open

        def safe_open(file, *args, **kwargs):
            if str(file).replace("\\", "/").endswith(
                ".cache/huggingface/token"
            ):
                return io.StringIO("DUMMY_TEST_ONLY")
            return real_open(file, *args, **kwargs)

        with mock.patch("builtins.open", side_effect=safe_open):
            from weaver import cards
        with mock.patch.object(
            cards.urllib.request, "build_opener",
            return_value=FakeOpener(http_error(404)),
        ):
            self.assertIsNone(cards.fetch_readme(REPO, "space"))
        with mock.patch.object(
            cards.urllib.request, "build_opener",
            return_value=FakeOpener(Response(b"owner-curated README")),
        ):
            self.assertEqual(cards.fetch_readme(REPO, "space"),
                             "owner-curated README")

    def test_head_reader_requires_exact_immutable_source_sha(self):
        sha = "f" * 40
        self.assertEqual(
            observed_head_sha(REPO, "space",
                              opener=FakeOpener(Response(
                                  json.dumps({"sha": sha}).encode()))),
            sha,
        )
        for invalid in (b"{}", b'{"sha":"main"}', b"{",
                        b"x" * 1_000_001):
            with (
                self.subTest(length=len(invalid)),
                self.assertRaises(SourceIntegrityHold),
            ):
                observed_head_sha(
                    REPO, "space", opener=FakeOpener(Response(invalid))
                )
        for code in (401, 403, 404, 429, 500):
            with (
                self.subTest(status=code),
                self.assertRaisesRegex(
                    SourceIntegrityHold, "SOURCE_HEAD_UNAVAILABLE"
                ),
            ):
                observed_head_sha(
                    REPO, "space", opener=FakeOpener(http_error(code))
                )

    def test_commit_payload_has_hf_parent_cas(self):
        real_open = builtins.open

        def safe_open(file, *args, **kwargs):
            if str(file).replace("\\", "/").endswith(
                ".cache/huggingface/token"
            ):
                return io.StringIO("DUMMY_TEST_ONLY")
            return real_open(file, *args, **kwargs)

        with mock.patch("builtins.open", side_effect=safe_open):
            from weaver import rollout_hf
        captured = []

        def fake_post(req, timeout):
            captured.append((req, timeout))
            return Response(b'{"sha":"fixture"}', status=200)

        with (
            mock.patch.object(
                rollout_hf.source_integrity, "assert_readme_unbound",
                return_value="SOURCE_MANIFEST_NOT_FOUND",
            ) as guard,
            mock.patch.object(
                rollout_hf.source_integrity, "observed_head_sha",
                return_value="f" * 40,
            ) as parent,
            mock.patch.object(
                rollout_hf.cardbox, "fetch_readme",
                return_value="# original owner card",
            ) as reread,
            mock.patch.object(
                rollout_hf.urllib.request, "urlopen",
                side_effect=fake_post,
            ),
        ):
            status, _ = rollout_hf.ndjson_commit(
                REPO, "space", [("README.md", "# fixture owner card")],
                expected_readme="# original owner card",
            )
        self.assertEqual(status, 200)
        self.assertEqual(guard.call_count, 2)
        parent.assert_called_once()
        reread.assert_called_once_with(REPO, "space")
        self.assertEqual(len(captured), 1)
        request, timeout = captured[0]
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(timeout, 180)
        header = json.loads(request.data.split(b"\n")[0])
        self.assertEqual(header["key"], "header")
        self.assertEqual(header["value"]["parentCommit"], "f" * 40)
        self.assertNotIn("DUMMY_TEST_ONLY", str(header))

    def test_stale_readme_and_manifest_race_never_write(self):
        from weaver import rollout_hf
        for cause in ("CHANGED_README", "SOURCE_MANIFEST_INTRODUCED"):
            with self.subTest(cause=cause):
                if cause == "CHANGED_README":
                    guards = [None, None]
                    current = "different README"
                    expected = "original README"
                    reason = "README_BASE_CHANGED"
                else:
                    guards = [
                        None, SourceIntegrityHold("SOURCE_MANIFEST_PRESENT")
                    ]
                    current = "original README"
                    expected = current
                    reason = "SOURCE_MANIFEST_PRESENT"
                with (
                    mock.patch.object(
                        rollout_hf.source_integrity, "assert_readme_unbound",
                        side_effect=guards,
                    ),
                    mock.patch.object(
                        rollout_hf.source_integrity, "observed_head_sha",
                        return_value="f" * 40,
                    ),
                    mock.patch.object(
                        rollout_hf.cardbox, "fetch_readme",
                        return_value=current,
                    ),
                    mock.patch.object(
                        rollout_hf.urllib.request, "urlopen",
                        side_effect=AssertionError("UNEXPECTED_PROVIDER_POST"),
                    ) as network,
                    self.assertRaisesRegex(SourceIntegrityHold, reason),
                ):
                    rollout_hf.ndjson_commit(
                        REPO, "space", [("README.md", "new card")],
                        expected_readme=expected,
                    )
                network.assert_not_called()

    def test_missing_host_readme_snapshot_cannot_write(self):
        from weaver import rollout_hf
        with (
            mock.patch.object(
                rollout_hf.source_integrity, "assert_readme_unbound",
                return_value="SOURCE_MANIFEST_NOT_FOUND",
            ),
            mock.patch.object(
                rollout_hf.source_integrity, "observed_head_sha",
                return_value="f" * 40,
            ),
            mock.patch.object(
                rollout_hf.urllib.request, "urlopen",
            ) as network,
            self.assertRaisesRegex(
                SourceIntegrityHold, "README_BASE_UNOBSERVED"
            ),
        ):
            rollout_hf.ndjson_commit(
                REPO, "space", [("README.md", "new card")]
            )
        network.assert_not_called()

    def test_ambiguous_post_and_quota_are_never_retried(self):
        from weaver import rollout_hf
        for outcome, status, code in (
            (TimeoutError("uncertain body"), 0, "COMMIT_OUTCOME_UNKNOWN"),
            # Simulated concurrent owner commit rejects old parentCommit.
            (http_error(409), 409, "COMMIT_HTTP_REFUSED"),
            (http_error(429), 429, "COMMIT_HTTP_REFUSED"),
            (http_error(503), 503, "COMMIT_HTTP_REFUSED"),
        ):
            with self.subTest(status=status):
                with (
                    mock.patch.object(
                        rollout_hf.source_integrity, "assert_readme_unbound",
                        return_value="SOURCE_MANIFEST_NOT_FOUND",
                    ),
                    mock.patch.object(
                        rollout_hf.source_integrity, "observed_head_sha",
                        return_value="f" * 40,
                    ),
                    mock.patch.object(
                        rollout_hf.cardbox, "fetch_readme",
                        return_value="original README",
                    ),
                    mock.patch.object(
                        rollout_hf.urllib.request, "urlopen",
                        side_effect=outcome,
                    ) as transport,
                ):
                    actual_status, actual_code = rollout_hf.ndjson_commit(
                        REPO, "space", [("README.md", "new card")],
                        expected_readme="original README",
                    )
                self.assertEqual(actual_status, status)
                self.assertEqual(actual_code, code)
                transport.assert_called_once()
                self.assertNotIn("uncertain body", actual_code)

if __name__ == "__main__":
    unittest.main()
