"""No-network synthetic tests for source-owned profile summary rendering."""
import unittest

from weaver.gen_profile_section import render


def fixture():
    return {
        "generated_at": "2026-11-20T03:48:04Z",
        "gh": {"total": 182},
        "hf_models": {"total": 413},
        "hf_datasets": {"total": 173},
        "hf_spaces": {"total": 2},
        "mesh": {"files": ["a", "b"]},
        "space_runtime": {"stages": {"one": "RUNNING", "two": "PAUSED"}},
    }


class ProfileRenderingTests(unittest.TestCase):
    def test_short_index_has_marker_and_not_false_full_fleet_claim(self):
        index, detail = render(fixture())
        self.assertLessEqual(len(index.split()), 35)
        self.assertIn("szl:estate-cards:v1 generated", index)
        self.assertIn("<!-- /szl:estate-cards:v1 -->", index)
        self.assertIn("ESTATE_AT_A_GLANCE.md", index)
        self.assertNotIn("all models operational", index.lower())
        self.assertIn("1/2 Spaces labeled RUNNING", detail)
        self.assertIn("182", detail)
        self.assertIn("413", detail)
        self.assertIn("not training completions", detail)

    def test_missing_runtime_is_unverified_not_zero(self):
        data = fixture()
        data.pop("space_runtime")
        self.assertIn("unavailable", render(data)[1])

    def test_partial_runtime_does_not_claim_fleet_stage(self):
        data = fixture()
        data["space_runtime"]["stages"].pop("two")
        self.assertIn("coverage incomplete", render(data)[1])

    def test_rejects_untrusted_counts_and_dates(self):
        for path, value in (
            (("gh", "total"), True),
            (("hf_models", "total"), -1),
            (("hf_datasets", "total"), "173"),
            (("hf_spaces", "total"), 1_000_001),
            (("generated_at",), "tomorrow"),
        ):
            data = fixture()
            if len(path) == 1:
                data[path[0]] = value
            else:
                data[path[0]][path[1]] = value
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    render(data)

    def test_rejects_missing_receipt_list(self):
        data = fixture()
        data["mesh"] = {}
        with self.assertRaises(ValueError):
            render(data)


if __name__ == "__main__":
    unittest.main()
