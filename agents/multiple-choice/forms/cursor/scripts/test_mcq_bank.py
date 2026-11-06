"""Checks for the multiple-choice input parser, scene sidecar, and item tally."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = Path(__file__).with_name("mcq_bank.py")
# examples/ sits beside the skill in a download, and two levels up in the catalog repo
SAMPLE = next(
    (path for path in (
        SKILL_ROOT / "examples" / "circular-motion-sample-input.yaml",
        SKILL_ROOT.parents[1] / "examples" / "circular-motion-sample-input.yaml",
    ) if path.exists()),
    SKILL_ROOT / "examples" / "circular-motion-sample-input.yaml",
)
SPEC = importlib.util.spec_from_file_location("mcq_bank", SCRIPT)
bank = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bank)


AXES = {
    "common": [
        {
            "id": "position",
            "values": ["top", "side", "bottom"],
            "changes_drawing": False,
        }
    ],
    "by_scenario": {
        "scenario 1": [],
        "scenario 2": [],
        "scenario 3": [
            {
                "id": "wind",
                "values": ["from the left", "from the right"],
                "changes_drawing": True,
            }
        ],
        "scenario 4": [
            {
                "id": "wind",
                "values": ["from the left", "from the right"],
                "changes_drawing": True,
            }
        ],
    },
}


class SampleInputTests(unittest.TestCase):
    def test_circular_motion_sample_has_the_current_fields(self):
        model = bank.parse_input(SAMPLE)
        report = bank.validate_model(model)
        self.assertTrue(report["ok"], report["errors"])
        self.assertEqual(report["scenarios"], ["scenario 1", "scenario 2", "scenario 3", "scenario 4"])
        self.assertEqual(report["possible_answers"], 3)
        self.assertEqual(report["distractors"], 3)
        self.assertEqual(report["candidates_per_scenario"], 4)
        self.assertEqual(report["samples_per_scenario"], 1)
        self.assertTrue(report["need_diagram"])
        self.assertTrue(report["export_yaml"])
        self.assertEqual(report["yaml_template"], bank.DEFAULT_TEMPLATE)
        self.assertFalse(report["correct_answer_blank"])
        self.assertIn("toward the center", model["correct_answer"])
        self.assertIn("replaces T with N", model["choice_variations"])
        self.assertEqual(len(model["scenarios"][2]["variations"]), 1)
        self.assertEqual(model["scenarios"][0]["variations"], [])


class BankFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.input_path = self.directory / "circular.yaml"
        self.input_path.write_text(SAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
        self.sidecar = bank.default_sidecar(self.input_path)

    def tearDown(self):
        self.temp.cleanup()

    def run_ok(self, func, *args):
        with self.assertRaises(SystemExit) as raised:
            func(*args)
        self.assertEqual(raised.exception.code, 0)

    def build_selected_bank(self):
        self.run_ok(bank.cmd_init, self.input_path, False)
        self.run_ok(bank.main, ["receive", "--file", str(self.sidecar)])
        for scenario in ("scenario 1", "scenario 2", "scenario 3", "scenario 4"):
            self.run_ok(
                bank.cmd_add,
                self.sidecar,
                scenario,
                [f"{scenario} scene A", f"{scenario} scene B"],
            )
        selection = {
            scenario: {"keep": [0], "backup": [1]}
            for scenario in ("scenario 1", "scenario 2", "scenario 3", "scenario 4")
        }
        selection_path = self.directory / "selection.json"
        axes_path = self.directory / "axes.json"
        selection_path.write_text(json.dumps(selection), encoding="utf-8")
        axes_path.write_text(json.dumps(AXES), encoding="utf-8")
        self.run_ok(bank.cmd_select, self.sidecar, selection_path)
        self.run_ok(bank.cmd_set_variations, self.sidecar, axes_path)

    def test_selection_tally_counts_kept_scenes_and_variation_values(self):
        self.build_selected_bank()
        self.assertEqual(len(bank.expected_items(bank.load_sidecar(self.sidecar))), 18)
        self.run_ok(bank.cmd_tally, self.sidecar)

    def test_check_items_rejects_a_backup_scene_and_a_distractor_marked_correct(self):
        self.build_selected_bank()
        data = bank.load_sidecar(self.sidecar)
        expected = bank.expected_items(data)
        good = []
        for item in expected:
            good.append(
                {
                    "scenario": item["scenario"],
                    "scene_index": item["scene_index"],
                    "values": item["values"],
                    "choices": ["a", "b", "c", "d", "e", "f"],
                    "correct_index": 0,
                    "choice_symbols": ["T", "m"],
                    "defines_symbols": ["T", "m", "g"],
                    "figure": f"{item['scenario']}-{item['drawing']}.png",
                }
            )
        items_path = self.directory / "items.json"
        items_path.write_text(json.dumps({"items": good}), encoding="utf-8")
        self.run_ok(bank.cmd_check_items, self.sidecar, items_path)

        good[0]["correct_index"] = 4
        good[1]["scene_index"] = 1
        items_path.write_text(json.dumps({"items": good}), encoding="utf-8")
        with self.assertRaises(SystemExit) as raised:
            bank.cmd_check_items(self.sidecar, items_path)
        self.assertEqual(raised.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
