"""Telemetry failures cannot be mistaken for successful command completion."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

from tools.claw.paths import WORK
from tools.claw.run_logged import main


class RunLoggedTests(unittest.TestCase):
    def test_success_failure_and_immutable_runs(self):
        WORK.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=WORK) as directory:
            records = []
            for code in (0, 7):
                with contextlib.redirect_stdout(io.StringIO()):
                    result = main(["--label", "synthetic-phase", "--directory", directory,
                                   "--", sys.executable, "-c", f"raise SystemExit({code})"])
                self.assertEqual(result, code)
                records = [json.loads(p.read_text()) for p in Path(directory).glob("*.json")]
            self.assertEqual(sorted(r["exit_code"] for r in records), [0, 7])
            self.assertEqual(len({r["run_id"] for r in records}), 2)
            for record in records:
                self.assertGreater(record["wall_seconds"], 0)
                self.assertGreaterEqual(record["child_user_seconds"], 0)
                self.assertNotIn("command_args", record)

    def test_rejects_tracked_output_directory_before_execution(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                main(["--label", "invalid", "--directory", "Tests", "--", "false"])
        self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
