import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


def load_selector():
    path = Path(__file__).parents[1] / "tools" / "select_today.py"
    spec = importlib.util.spec_from_file_location("select_today", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RosterFreezeTest(unittest.TestCase):
    def setUp(self):
        self.selector = load_selector()
        self.tmp = Path(tempfile.mkdtemp())
        self.selector.REPO = self.tmp
        self.selector.ROSTER_DIR = self.tmp / "rosters"

    def test_existing_roster_is_reused_without_reselection(self):
        path = self.selector.roster_path("2026-07-09")
        path.parent.mkdir()
        original = {
            "date": "2026-07-09",
            "items": [{"qid": "2024-07"}, {"qid": "2024-08"}],
        }
        path.write_text(json.dumps(original), encoding="utf-8")

        self.assertEqual(self.selector.load_existing_roster("2026-07-09"), original)

    def test_invalid_existing_roster_is_never_replaced(self):
        path = self.selector.roster_path("2026-07-09")
        path.parent.mkdir()
        path.write_text(json.dumps({"date": "2026-07-09", "items": []}), encoding="utf-8")

        with self.assertRaises(SystemExit):
            self.selector.load_existing_roster("2026-07-09")
