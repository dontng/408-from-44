import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


def load_progress():
    path = Path(__file__).parents[1] / "tools" / "progress.py"
    spec = importlib.util.spec_from_file_location("progress", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProgressLedgerTest(unittest.TestCase):
    def setUp(self):
        self.progress = load_progress()
        self.tmp = Path(tempfile.mkdtemp())
        self.progress.EVENT_DIR = self.tmp / "progress"
        self.progress.BASELINE_FILE = self.progress.EVENT_DIR / "baseline.json"
        self.progress.STATE_FILE = self.tmp / "state.json"
        self.progress.write_json(self.progress.STATE_FILE, {"2024-01": {"box": 0, "seen": 0, "right": 0}})

    def result(self, ok=True, year="2024", q=1):
        return {"date": "2026-07-05", "items": [{
            "qid": f"{year}-{q:02d}", "year": year, "q": q, "source": "new",
            "pick": "A", "answer": "A", "status": "right" if ok else "wrong", "ok": ok,
        }]}

    def test_regrading_replaces_the_daily_event(self):
        self.progress.record_day(self.result(), {"2024-01": "solid"})
        self.progress.record_day(self.result(), {"2024-01": "solid"})
        state = self.progress.read_json(self.progress.STATE_FILE, {})
        events = self.progress.read_json(self.progress.EVENT_DIR / "0705.json", {})["events"]
        self.assertEqual(state["2024-01"]["seen"], 1)
        self.assertEqual(len(events), 1)
        self.assertFalse(state["2024-01"]["stuck"])

    def test_provisional_answers_are_not_marked_official(self):
        self.progress.record_day(self.result(year="2025", q=8), {})
        state = self.progress.read_json(self.progress.STATE_FILE, {})
        self.assertEqual(state["2025-08"]["answer_confidence"], "provisional_low")
