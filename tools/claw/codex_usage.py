"""Audit recent Codex sessions using structured rollout events, never transcript text.

Run ``python -m tools.claw.codex_usage [--days 7]``. Logs remain read-only.
A session belongs here if session_meta.cwd or turn_context.cwd is within a
known checkout. Budgets cover that whole session, including any other cwd.
"""
import glob
import json
import os
from pathlib import Path
import sys
import time

MAX_TURNS = 150
MAX_TOKENS = 40_000_000  # OPERATING.md says "about 30 million"; 30-37M single-turn runs are mostly cached context
# The second root is the original checkout, retained in historical rollout cwd.
REPOSITORY_ROOTS = (
    Path(__file__).resolve().parents[2],
    Path.home() / "Documents/Codex/2026-10-11/claw-ipad",
)
TURN_EVENTS = {"task_started", "task_complete", "turn_aborted"}


def _in_repository(cwd, roots):
    if not isinstance(cwd, str) or not Path(cwd).is_absolute():
        return False
    location = Path(cwd).resolve()
    return any(location == root or root in location.parents for root in roots)


def sessions(days, *, log_root=None, repo_roots=None, now=None):
    """Yield whole-session usage for logs active in the unchanged mtime window.

    Current logs identify turns with turn_id on turn_context and lifecycle
    events. The union also includes unfinished/aborted turns and avoids counting
    repeated context updates. root_turn_id may group different worker turns and
    is deliberately not the identity. For older logs without any turn IDs, use
    task_started records, or conservatively count turn_context records if absent.
    Token reports are cumulative telemetry, not turns or additive deltas.
    """
    cutoff = (time.time() if now is None else now) - days * 86400
    log_root = Path(log_root) if log_root is not None else Path.home() / ".codex/sessions"
    roots = tuple(Path(root).resolve() for root in (REPOSITORY_ROOTS if repo_roots is None else repo_roots))
    for path in glob.glob(str(log_root / "*/*/*/rollout-*.jsonl")):
        if os.path.getmtime(path) < cutoff:
            continue
        mine, peak, model = False, None, None
        turn_ids = set()
        starts = contexts = reports = 0
        session_id = Path(path).stem[8:]
        with open(path, "rb") as stream:
            for line in stream:
                try:
                    record = json.loads(line)
                except ValueError:
                    # A live rollout may end in an incomplete line.
                    continue
                if not isinstance(record, dict):
                    continue
                kind, payload = record.get("type"), record.get("payload")
                if not isinstance(payload, dict):
                    continue
                if kind in ("session_meta", "turn_context"):
                    mine = mine or _in_repository(payload.get("cwd"), roots)
                if kind == "session_meta":
                    session_id = payload.get("id") or session_id
                if kind == "turn_context":
                    contexts += 1
                    model = payload.get("model", model)
                subtype = payload.get("type") if kind == "event_msg" else None
                if subtype == "task_started":
                    starts += 1
                if kind == "turn_context" or subtype in TURN_EVENTS:
                    turn_id = payload.get("turn_id")
                    if isinstance(turn_id, str) and turn_id:
                        turn_ids.add(turn_id)
                if subtype == "token_count":
                    info = payload.get("info")
                    usage = info.get("total_token_usage") if isinstance(info, dict) else None
                    if not isinstance(usage, dict):
                        continue
                    total = usage.get("total_tokens")
                    if type(total) is not int or total < 0:
                        continue
                    reports += 1
                    # A stale/reset report must not erase an already seen breach.
                    if peak is None or total >= peak["total_tokens"]:
                        peak = usage
        if not mine:
            continue
        source = "turn_id" if turn_ids else "task_started" if starts else "turn_context"
        usage = peak or {}
        yield {"session": os.path.basename(path)[8:27], "session_id": session_id,
               "turns": len(turn_ids) if turn_ids else starts or contexts,
               "turn_count_source": source, "model": model, "token_reports": reports,
               "usage_available": peak is not None, "total": usage.get("total_tokens", 0),
               "uncached_input": usage.get("input_tokens", 0) - usage.get("cached_input_tokens", 0),
               "output": usage.get("output_tokens", 0)}


# Sessions that started before the session budget existed are reported but never fail the check.
RULES_SINCE = "2026-10-15T01-30-00"


def main(argv):
    days = int(argv[argv.index("--days") + 1]) if "--days" in argv else 7
    since = argv[argv.index("--since") + 1] if "--since" in argv else RULES_SINCE
    found = sorted(sessions(days), key=lambda s: -s["total"])
    long = [s for s in found if (s["turns"] > MAX_TURNS or s["total"] > MAX_TOKENS) and s["session"] >= since]
    for s in found[:10]:
        flag = "  OVER BUDGET" if s in long else ""
        print(f"{s['session']}  {s['turns']:5d} turns  {s['total'] / 1e6:7.1f}M total  {s['output'] / 1e6:5.2f}M out  {s['model']}{flag}")
    total = sum(s["total"] for s in found)
    print(json.dumps({"command": "codex-usage", "days": days, "sessions": len(found), "total_tokens": total,
                      "uncached_input": sum(s["uncached_input"] for s in found),
                      "output": sum(s["output"] for s in found), "over_budget_sessions": len(long),
                      "tokens_in_over_budget_sessions": sum(s["total"] for s in long),
                      "over_budget": long,
                      "budget": {"turns": MAX_TURNS, "tokens": MAX_TOKENS}, "counted_since": since,
                      "status": "pass" if not long else "fail"}))
    return 1 if long else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
