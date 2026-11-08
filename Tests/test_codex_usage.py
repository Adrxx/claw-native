"""Synthetic regressions for repository session accounting; never read real logs."""
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.claw import codex_usage


class CodexUsageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.logs = self.root / "sessions"
        self.repo = self.root / "claw-ipad"
        self.other = self.root / "other"
        self.now = 1_800_000_000

    @staticmethod
    def meta(cwd, session_id="synthetic-session"):
        return {"type": "session_meta", "payload": {"id": session_id, "cwd": str(cwd)}}

    @staticmethod
    def context(cwd, turn_id=None, **extra):
        payload = {"cwd": str(cwd), "model": "synthetic-model", **extra}
        if turn_id is not None:
            payload["turn_id"] = turn_id
        return {"type": "turn_context", "payload": payload}

    @staticmethod
    def event(kind, **extra):
        return {"type": "event_msg", "payload": {"type": kind, **extra}}

    @classmethod
    def tokens(cls, total, **extra):
        usage = {"total_tokens": total, "input_tokens": total - 10,
                 "cached_input_tokens": 20, "output_tokens": 10}
        return cls.event("token_count", info={"total_token_usage": usage, **extra})

    def write_log(self, name, records, *, mtime=None):
        path = self.logs / "2026" / "10" / "15" / f"rollout-{name}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(record) + "\n" for record in records))
        timestamp = self.now if mtime is None else mtime
        os.utime(path, (timestamp, timestamp))
        return path

    def rows(self):
        return list(codex_usage.sessions(7, log_root=self.logs,
                                        repo_roots=[self.repo], now=self.now))

    def test_session_metadata_cwd_attributes_nested_directory(self):
        self.write_log("owned", [self.meta(self.repo / "App"), self.tokens(100)])
        row, = self.rows()
        self.assertEqual(row["session_id"], "synthetic-session")
        self.assertEqual(row["total"], 100)
        self.assertTrue(row["usage_available"])

    def test_turn_context_attributes_whole_mixed_cwd_session(self):
        self.write_log("mixed", [self.meta(self.other), self.tokens(100),
                                self.context(self.repo / "Tests", "one"),
                                self.context(self.other, "two"), self.tokens(300)])
        row, = self.rows()
        self.assertEqual(row["total"], 300)
        self.assertEqual(row["turns"], 2)

    def test_text_embedded_json_workspace_roots_and_sibling_prefix_do_not_attribute(self):
        decoys = [
            self.meta(self.other),
            self.context(self.repo.with_name("claw-ipad-copy"), "one",
                         workspace_roots=[str(self.repo)]),
            self.event("user_message", message=str(self.repo)),
            self.event("agent_message", message=json.dumps(self.meta(self.repo))),
            {"type": "response_item", "payload": {"type": "message", "content": [
                {"type": "input_text", "text": str(self.repo)}]}},
            self.tokens(100),
        ]
        self.write_log("decoys", decoys)
        self.assertEqual(self.rows(), [])

    def test_attribution_is_not_limited_to_first_sixty_lines(self):
        self.write_log("late", [self.meta(self.other)] +
                       [self.event("agent_message", message="filler")] * 65 +
                       [self.context(self.repo, "late"), self.tokens(100)])
        self.assertEqual(len(self.rows()), 1)

    def test_distinct_turn_ids_deduplicate_events_and_include_aborted_unfinished(self):
        self.write_log("turns", [
            self.meta(self.repo),
            self.context(self.repo, "a", root_turn_id="root"),
            self.context(self.repo, "a", root_turn_id="root"),
            self.event("task_started", turn_id="a"),
            self.event("task_complete", turn_id="a"),
            self.context(self.repo, "b", root_turn_id="root"),
            self.event("turn_aborted", turn_id="b"),
            self.event("task_started", turn_id="unfinished"),
            self.event("task_complete", turn_id="complete-only"),
            self.tokens(100), self.tokens(200), self.tokens(300),
        ])
        row, = self.rows()
        self.assertEqual(row["turns"], 4)
        self.assertEqual(row["token_reports"], 3)
        self.assertEqual(row["turn_count_source"], "turn_id")

    def test_legacy_task_started_fallback_does_not_count_token_reports(self):
        self.write_log("legacy-starts", [self.meta(self.repo),
                       self.context(self.repo), self.context(self.repo),
                       self.event("task_started"), self.event("task_started"),
                       self.event("task_started"), self.tokens(100), self.tokens(200)])
        row, = self.rows()
        self.assertEqual(row["turns"], 3)
        self.assertEqual(row["turn_count_source"], "task_started")

    def test_legacy_context_fallback_and_token_only_session(self):
        self.write_log("legacy-context", [self.meta(self.repo, "contexts"),
                       self.context(self.repo), self.context(self.repo), self.tokens(100)])
        self.write_log("token-only", [self.meta(self.repo, "tokens"),
                       self.tokens(100), self.tokens(200), self.tokens(300)])
        rows = {row["session_id"]: row for row in self.rows()}
        self.assertEqual(rows["contexts"]["turns"], 2)
        self.assertEqual(rows["contexts"]["turn_count_source"], "turn_context")
        self.assertEqual(rows["tokens"]["turns"], 0)

    def test_peak_cumulative_snapshot_wins_without_summing_or_using_last_usage(self):
        self.write_log("peak", [self.meta(self.repo), self.tokens(100),
                       self.tokens(500, last_token_usage={"total_tokens": 999_999}),
                       self.tokens(200),
                       self.event("token_count", info={"total_token_usage": None}),
                       self.event("agent_message", info={"total_token_usage": {
                           "total_tokens": 999_999}})])
        row, = self.rows()
        self.assertEqual(row["total"], 500)
        self.assertEqual(row["uncached_input"], 470)
        self.assertEqual(row["output"], 10)

    def test_duplicate_cumulative_reports_do_not_inflate_turns_or_tokens(self):
        self.write_log("duplicates", [self.meta(self.repo),
                       self.context(self.repo, "only-turn")] + [self.tokens(100)] * 151)
        row, = self.rows()
        self.assertEqual(row["turns"], 1)
        self.assertEqual(row["total"], 100)
        self.assertEqual(row["token_reports"], 151)
        status, report = self.run_main([row])
        self.assertEqual(status, 0)
        self.assertEqual(report["over_budget_sessions"], 0)

    def test_malformed_and_truncated_lines_preserve_valid_accounting(self):
        path = self.write_log("truncated", [self.meta(self.repo),
                              self.context(self.repo, "one"), self.tokens(100)])
        with path.open("a") as stream:
            stream.write('not json\n[]\n{"type":"event_msg","payload":')
        os.utime(path, (self.now, self.now))
        row, = self.rows()
        self.assertEqual(row["turns"], 1)
        self.assertEqual(row["total"], 100)

    def test_session_without_token_usage_is_retained(self):
        self.write_log("no-tokens", [self.meta(self.repo), self.context(self.repo, "one")])
        row, = self.rows()
        self.assertFalse(row["usage_available"])
        self.assertEqual(row["total"], 0)
        self.assertEqual(row["token_reports"], 0)
        self.assertEqual(row["turns"], 1)

    def test_seven_day_window_uses_inclusive_file_mtime_cutoff(self):
        cutoff = self.now - 7 * 86400
        for name, timestamp in [("older", cutoff - 1), ("boundary", cutoff),
                                ("newer", cutoff + 1)]:
            self.write_log(name, [self.meta(self.repo, name), self.tokens(100)],
                           mtime=timestamp)
        self.assertEqual({row["session_id"] for row in self.rows()}, {"boundary", "newer"})

    @staticmethod
    def cli_row(name, *, turns=1, total=100):
        return {"session": name, "session_id": name, "turns": turns,
                "model": "synthetic-model", "total": total, "uncached_input": 0,
                "output": 0, "token_reports": 1, "turn_count_source": "turn_id",
                "usage_available": True}

    def run_main(self, rows):
        stream = io.StringIO()
        with patch.object(codex_usage, "sessions", return_value=iter(rows)) as read:
            with contextlib.redirect_stdout(stream):
                status = codex_usage.main(["--days", "7"])
        read.assert_called_once_with(7)
        return status, json.loads(stream.getvalue().splitlines()[-1])

    def test_cli_exact_thresholds_pass(self):
        status, report = self.run_main([self.cli_row("limit", turns=150, total=30_000_000)])
        self.assertEqual(status, 0)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["over_budget"], [])

    def test_cli_over_budget_rows_and_tokens_use_true_failures(self):
        tokens = self.cli_row("tokens-over", total=30_000_001)
        turns = self.cli_row("turns-over", turns=151, total=1_000)
        safe = self.cli_row("safe", turns=150, total=30_000_000)
        status, report = self.run_main([safe, turns, tokens])
        self.assertEqual(status, 1)
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["over_budget_sessions"], 2)
        self.assertEqual(report["tokens_in_over_budget_sessions"], 30_001_001)
        self.assertEqual(report["over_budget"], [tokens, turns])

    def test_real_synthetic_over_budget_log_fails_cli_after_lower_snapshot(self):
        self.write_log("actual-breach", [self.meta(self.repo, "breach"),
                       self.context(self.repo, "one"), self.tokens(30_000_001),
                       self.tokens(100)])
        rows = self.rows()
        status, report = self.run_main(rows)
        self.assertEqual(status, 1)
        self.assertEqual(report["total_tokens"], 30_000_001)
        self.assertEqual(report["tokens_in_over_budget_sessions"], 30_000_001)
        self.assertEqual(report["over_budget"], rows)
        self.assertEqual(report["over_budget"][0]["turns"], 1)


if __name__ == "__main__":
    unittest.main()
