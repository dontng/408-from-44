import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SpeedrunToolTest(unittest.TestCase):
    def test_scaffold_uses_immutable_attempt_evidence(self):
        result = json.loads((REPO / "data/results/0712.json").read_text(encoding="utf-8"))
        new_speedrun = load_module("new_speedrun", REPO / "tools/new_speedrun.py")
        text = new_speedrun.render_session(result)
        self.assertIn("## 01｜2024-25：待命名机制", text)
        self.assertIn("首次作答：D；正确答案：D；当前状态：`draft`", text)
        self.assertIn("## 20｜2023-10：待命名机制", text)
        self.assertEqual(text.count("### 最小验证"), 20)

    def test_cli_generates_without_touching_repository_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "0712.md"
            subprocess.run(
                [
                    "python3",
                    str(REPO / "tools/new_speedrun.py"),
                    "--date",
                    "0712",
                    "--output",
                    str(output),
                ],
                cwd=REPO,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertTrue(output.exists())
            self.assertIn("# 0712｜速通草稿", output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
