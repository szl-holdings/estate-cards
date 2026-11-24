"""Check the counts and proportions readers see in inventory charts."""
import unittest
from xml.etree import ElementTree as ET

from weaver import cards, charts


class DonutCountsTest(unittest.TestCase):
    def test_no_observations_are_unknown(self):
        svg = ET.fromstring(charts.donut([], title="Inventory"))
        labels = [node.text for node in svg.findall("{*}text")]
        self.assertIn("Inventory", labels)
        self.assertIn("no admissible data - UNKNOWN", labels)
        self.assertFalse(any(label.isdecimal() for label in labels))

    def test_model_card_shows_zero_when_every_count_is_measured_zero(self):
        audit = {key: {"total": 0} for key in ("hf_models", "hf_datasets", "hf_spaces")}
        audit["generated_at"] = "2026-11-23T00:00:00Z"
        _, assets = cards.model_card("SZLHOLDINGS/example", audit)
        svg = ET.fromstring(assets["org-context.svg"])
        labels = [node.text for node in svg.findall("{*}text")]
        self.assertEqual([text for text in labels if text.isdecimal()], ["0"])
        self.assertIn("models: 0", labels)
        self.assertEqual(svg.findall("{*}path") + svg.findall("{*}circle"), [])

    def test_one_nonzero_category_has_a_full_ring_in_its_own_color(self):
        svg = ET.fromstring(charts.donut([("paused", 0), ("running", 3, "#123456")]))
        ring, = svg.findall("{*}circle")
        self.assertEqual(ring.get("stroke"), "#123456")
        self.assertEqual(ring.get("fill"), "none")
        self.assertGreater(float(ring.get("stroke-width")), 0)
        self.assertEqual(svg.findall("{*}path"), [])
        labels = [node.text for node in svg.findall("{*}text")]
        self.assertIn("3", labels)
        self.assertIn("running: 3", labels)

    def test_mixed_counts_keep_two_sectors_and_the_total(self):
        svg = ET.fromstring(charts.donut([("models", 3), ("datasets", 2)]))
        paths = svg.findall("{*}path")
        self.assertEqual(len(paths), 2)
        self.assertEqual(
            [path.get("d") for path in paths],
            [
                "M 85.00 8.00 A 77.00 77.00 0 1 1 39.74 147.29 L 56.94 123.62 A 47.74 47.74 0 0 0 85.00 37.26 Z",
                "M 39.74 147.29 A 77.00 77.00 0 0 1 85.00 8.00 L 85.00 37.26 A 47.74 47.74 0 0 0 56.94 123.62 Z",
            ],
        )
        labels = [node.text for node in svg.findall("{*}text")]
        self.assertIn("5", labels)
        self.assertIn("models: 3", labels)
        self.assertIn("datasets: 2", labels)

    def test_invalid_counts_do_not_render_a_proportion(self):
        for value in (-1, float("nan"), float("inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                charts.donut([("models", 2), ("datasets", value)])
