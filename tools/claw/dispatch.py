"""Works through tools/queue.json, one fresh Codex run per task. No model acts as the dispatcher.

    python -m tools.claw.dispatch [--lane N] [--family-only | --app-only] [--until <task id>] [--max-tasks N] [--dry-run]

For each task from `queue next` it starts `codex exec` with the task's model, waits for it, and reads back the task's
state from the queue. It stops when the --until task is done, the queue has nothing for agents, two tasks in a row end
blocked, a run leaves its task unrecorded twice, a health check fails, or work/dispatch/STOP exists (checked between
tasks). Several lanes may run at once, one process each (--lane 1, 2, 3). A lane claims its task under the queue
lock before starting Codex, takes only tasks whose depends_on are done, and runs a serial task (anything that is not a
family admission, batch or recovery) only while no other serial task is taken. A task that changes the shared harness
(marked "exclusive", or named for harness, ABI, x87, transport or callback work) runs only when no other task is taken,
and while it runs nothing else starts. A lane with nothing ready waits while
other lanes work. A STOP file stops a lane only if it was created after the lane started. Codex runs at low priority
with the gate limited to one mutation job. Admissions, batches and recoveries start on the cheaper model; a cheaper
run that ends blocked (not merely waiting on queued prerequisites) or unrecorded is retried once on the strong model.
A task blocked while it waits on queued prerequisites is reopened automatically and runs once they are done. Logs go to work/dispatch/<start time>-L<lane>/.
"""
import datetime
import json
import os
import re
import subprocess
import sys
import time

from . import queue as task_queue
from .paths import PYTHON, ROOT, WORK

MODELS = {"strong": ("gpt-6-astra", "high"), "cheaper": ("gpt-6.1-sol", "medium")}
TASK_TIMEOUT = 3 * 3600
PROMPT = """Work in {root}. Read AGENTS.md, CLAUDE.md and docs/OPERATING.md, and nothing else unless your task names it.
Your task is `{id}`: {title}. Its full entry is in tools/queue.json.
It is already claimed for you (`make take ID={id}` confirms it). Do it, and check it with its done_when.
End with `make finish ID={id} NOTE="<what is now true and the command that shows it>"`, or, if you cannot finish,
`make block ID={id} NOTE="<what is needed, from whom>"`. If the task is too big for one session (about an hour or 100 turns of work,
as docs/OPERATING.md says), and only then, add bounded follow-up
tasks to tools/queue.json before the task that needs them, finish what you did, and stop.
Finishing part of a task in under 45 minutes and queueing the rest is a mistake unless the rest truly waits on
another task's result: keep working instead. Owner decision 2026-10-27: too many runs end blocked after two or three
minutes with a new tiny follow-up. Before blocking, fix small missing pieces yourself (a transport entry, a project
membership, a native service stub) when they are within reach of your task; queue at most one follow-up per run, and
only for work that is clearly separate and substantial. Stop at 150 turns even if unfinished: record where you are with `make block` and end. Do not take a second task.
Two other Codex sessions work in this checkout at the same time on other tasks. Run heavy jobs (gate, builds,
emulation) one at a time, edit only the files your task needs, and re-read tools/queue.json right before you edit it.
Never edit the shared harness (Tests/clawparity/) unless your task has "exclusive": true; the dispatcher runs those
tasks alone, and every harness change forces hours of re-gating, so bundle all harness changes you know of into one task.
Only follow-ups that change Tests/clawparity/ get "exclusive": true. Per-level tooling (Tests/NativeLevels/, level
plans) is not exclusive: give such follow-ups "exclusive": false and "parallel": true. App tasks (ids starting app-) are
never parallel; the app lanes run them two at a time.
Rules learned in October 2026, which every agent on this project follows:
- Use fresh sub-agents for the case-author and translator roles (docs/OPERATING.md). As coordinator you never edit translation
  sources (Sources/*Runtime.cpp) or cases yourself. If the gate's mutation score is short, send the case author back for cases
  that kill the survivors; never relax a threshold and never record a mutant as equivalent without checking the original.
- Keep each family to at most about 600 cases (the gate reruns every case for about 48 mutants; thousands make a gate take
  hours) and make coverage independent of the random seed.
- Coverage exemptions only where the original itself faults or provably cannot execute, each reason checked against the
  original (null operator new then a null read; the MFC table-grow failure via 0x4db6e0 -> 0x4dc680, which zeroes EBP; a
  compare that can never differ). Anything blocked by a missing harness stand-in or register context is an exclusive
  follow-up task, never an exemption. Never patch import slots ad hoc in cases; declare fixtures in the spec.
- Harness facts: declared fixtures exist for realloc (0x4a9070), IsBadReadPtr, SetRect and SetRectEmpty; a caller_frame callee
  declaration supplies the caller's EBP (0x4dbd60, 0x4dbe10); balanced and exact x87 transport and owned x87 returns are
  supported; families may borrow admitted sources with shared_sources. See Tests/clawparity/README.md.
- If `Tests.NativeLevelOne.check` or `Tests.NativeEndOfLevel.check` fails only on census counts, do not edit the census
  contract and do not block on it; the orchestrator reconciles it.
{app_rules}
- Never paste decompiled or disassembled text into tracked files.
- Readability tasks: never queue follow-up re-gate, consumer-validation or revalidation tasks for families stale only because
  another readability chain edited a shared header; readability-final-revalidation re-gates all of them once at the end.
- Never create launchd jobs, cron entries, login items or any other persistent service on this Mac; run long work in your
  own session and block with a note if it cannot finish.
Do not commit or push."""

NO_APP = """- Do not run xcodebuild or open the Claw app; the app lane does app work.
- Check `sysctl -n vm.loadavg` before every gate, trace or other heavy job and wait while it is 16 or more.
- Disk is tight: keep at most four emulator checkpoints per level map (about 0.3 GB each) and delete older ones."""
APP_RULES = """- You may build and run the Mac app: `make project`, then scripts/run-mac.sh (it waits by itself while the load is 16 or
  more). Check `sysctl -n vm.loadavg` before every gate, trace or app run and wait while it is 16 or more. High load from
  other projects is normal on this Mac: keep waiting and retrying; never block a task only because of load.
- Every Claw launch you make passes --mute (the owner works next to this Mac; verify sound offline, never through the
  speakers). Close only Claw instances you started, by pid. Never kill a Claw instance launched without --mute: it is the
  owner's, who may be playing. Check real input with real key events and confirmed delivery (scripts/real_input.py).
- Two app sessions work in this checkout at once. Build and launch only through scripts/run-mac.sh and the check scripts,
  which use your own build folder ($CLAW_DERIVED_DATA); never create other build folders (each costs 1-2 GB of a tight disk); keep at most four
  emulator checkpoints per level map (about 0.3 GB each) and delete older ones you no longer need; per-frame PNG dumps cost about 0.6 GB per
  attempt: once an attempt is recorded in JSON (or abandoned), delete its PNG frames and keep only the frames of the first mismatch; keep source edits small and focused, re-read a file right before
  patching it, and if a build fails in a file you did not touch, wait a few minutes and rebuild before investigating.
- Testing (owner decision 2026-10-25): move forward, test little. Run only the checks your change directly touches
  (regressions.sh takes check names; scripts/check-*.py), and none if your task changed no app code (App/, Sources/,
  scripts/check-*.py, work/new-game/). Do not run the full regressions.sh suite; a daily full run catches regressions.
  If a check fails, rerun it alone once before calling it real. Every task that fixes or adds behavior adds a check for
  it (new levels, later parts of levels, bosses, menu pages). Finish with a fresh Release build in
  work/MacCatalyst/Build/Products/Release-maccatalyst.
- Levels are finished with the owner-approved MPSCULLY cheat, never by play; after Level N comes Level N+1 like the original."""

PARALLEL_SAFE = ("menu-admit-", "menu-batch-", "recover-", "admit-")
HARNESS_WORDS = re.compile(r"harness|abi|x87|transport|stack-input|callback|clawparity")
WAIT_SECONDS = 60
REGATING = WORK / "dispatch" / "REGATING"


def run(command, **options):
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, **options)


def health(since):
    results = {}
    for name, command in (("usage", ["-m", "tools.claw", "usage", "--since", since]), ("disk", ["-m", "tools.claw", "disk"]),
                          ("lint-docs", ["-m", "tools.claw", "lint-docs"])):
        done = run([str(PYTHON), *command])
        try:
            results[name] = json.loads(done.stdout.strip().splitlines()[-1]).get("status")
        except (IndexError, ValueError):
            results[name] = "error"
    return results


def log(directory, record):
    with open(directory / "dispatch.jsonl", "a") as sink:
        sink.write(json.dumps(record) + "\n")
    print(json.dumps(record), flush=True)


def ready(task, states):
    return task["state"] == "open" and task["model"] != "owner" and all(
        states.get(d, "done") == "done" for d in task.get("depends_on", []))


FAMILY_WORK = re.compile(r"(^|-)(admit|batch|recover|admission)(-|$)")


def serial(task):
    if task.get("parallel") and not task["id"].startswith("app-"):
        # Marked safe beside other work (for example a level's native join once the join tooling is level-generic).
        return False
    integration = re.search(r"join|on-screen|native-|app-", task["id"])
    return not (task["id"].startswith(PARALLEL_SAFE) or FAMILY_WORK.search(task["id"])) or exclusive(task) or bool(integration)


def exclusive(task):
    """Harness changes run alone: a gate running beside them would measure a half-edited harness."""
    if task.get("exclusive") is False:
        return False  # explicitly marked safe beside other work, even if its name sounds like harness work
    return bool(task.get("exclusive")) or bool(HARNESS_WORDS.search(task["id"]))


def model_for(task):
    """Admissions, batches and recoveries start on the cheaper model; the gate judges their result either way.
    Owner decision 2026-10-26: everything else, app and join tasks included, also starts on the cheaper model; harness
    changes and anything escalated after a cheaper run left no result use the strong model."""
    if task.get("escalated") or exclusive(task):
        return MODELS["strong"]
    return MODELS["cheaper"]


def reopen_waiting(queue, states):
    """A task blocked while it waits on queued prerequisites goes back to open; ready() holds it until they are done."""
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    for task in queue["tasks"]:
        waits = [d for d in task.get("depends_on", []) if states.get(d, "done") != "done"]
        if task["state"] == "blocked" and waits:
            task.pop("claimed_by", None)
            task.update(state="open", reopened=stamp, reopen_reason="dispatcher: waits on " + ", ".join(waits))
            states[task["id"]] = "open"


FAMILY_ONLY = False
APP_ONLY = False
SERIAL_SLOTS = 4      # 2026-10-27: family work ran out; each lane has its own build folder
MAX_TAKEN = 4      # three lanes plus one Claude-held task stay within the four-heavy-jobs limit


DAILY_RUNS = 300      # owner 2026-10-27 night: go past the old 150 limit; still a runaway guard
DAILY_STRONG_RUNS = 60


def runs_today():
    """Codex runs started today across all lanes, and how many of them used the strong model."""
    today = datetime.date.today().strftime("%Y-%m-%d")
    total = strong = 0
    for log in (WORK / "dispatch").glob(f"{today}T*-L*/dispatch.jsonl"):
        for line in log.read_text(errors="ignore").splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if event.get("event") == "start":
                total += 1
                strong += event.get("model") == MODELS["strong"][0]
    return total, strong


def claim(lane):
    """Pick and mark the next ready task for this lane; None when nothing is ready."""
    with task_queue.locked():
        queue = task_queue.load()
        states = {t["id"]: t["state"] for t in queue["tasks"]}
        reopen_waiting(queue, states)
        task_queue.save(queue)
        taken = [t for t in queue["tasks"] if t["state"] == "taken"]
        if len(taken) >= MAX_TAKEN:
            # Project limit: at most four heavy jobs at once, whichever lanes (or orphaned runs) hold them.
            return None, True
        regating = REGATING.exists()
        if regating and len(taken) >= 2:
            # The re-gate itself runs two gate jobs; keep the total within the four-heavy-jobs limit.
            return None, True
        if any(exclusive(t) for t in taken):
            return None, True
        # Two app lanes may each run one serial task (separate build folders); exclusive tasks still run alone.
        serial_busy = sum(1 for t in taken if serial(t)) >= SERIAL_SLOTS
        candidates = [t for t in queue["tasks"] if ready(t, states)]
        if regating:
            # Stale admissions block `make project` and app builds until the re-gate finishes, so only family work
            # that never builds the app may start meanwhile.
            candidates = [t for t in candidates if not serial(t) and not exclusive(t)]
        if candidates and exclusive(candidates[0]) and (APP_ONLY or FAMILY_ONLY and
                                                         not any(serial(t) and not exclusive(t) for t in taken)):
            # An exclusive task heads the queue: restricted lanes take nothing new so the others drain and it can run.
            # While a serial task runs the exclusive one cannot start anyway, so batch lanes keep working until it ends.
            return None, True
        if FAMILY_ONLY:
            # Codex lanes take only family batches; the Claude orchestrator takes harness, integration and app work.
            candidates = [t for t in candidates if not serial(t) and not exclusive(t)]
        if APP_ONLY:
            # The app lane takes integration, app, join and harness work, one at a time.
            candidates = [t for t in candidates if serial(t) or exclusive(t)]
        if candidates and exclusive(candidates[0]):
            # Drain the other lanes rather than starve the harness task that later work depends on.
            candidates = [] if taken else candidates[:1]
        for task in candidates:
            if not (serial(task) and serial_busy):
                task.update(state="taken", taken=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                            claimed_by=f"dispatcher lane {lane}")
                task_queue.save(queue)
                return task, False
        return None, any(t["state"] == "taken" for t in queue["tasks"])


def main(argv):
    until = argv[argv.index("--until") + 1] if "--until" in argv else None
    limit = int(argv[argv.index("--max-tasks") + 1]) if "--max-tasks" in argv else 1000
    lane = int(argv[argv.index("--lane") + 1]) if "--lane" in argv else 1
    global FAMILY_ONLY, APP_ONLY
    FAMILY_ONLY = "--family-only" in argv
    APP_ONLY = "--app-only" in argv
    started = datetime.datetime.now()
    since = started.strftime("%Y-%m-%dT%H-%M-%S")
    directory = WORK / "dispatch" / f"{since}-L{lane}"
    directory.mkdir(parents=True, exist_ok=True)
    stop_file = WORK / "dispatch" / "STOP"
    blocked_in_a_row, unrecorded, count, reason = 0, {}, 0, "task limit reached"
    environment = {**os.environ, "CLAW_GATE_JOBS": "1", "CLAW_AGENT": "1",
                   "CLAW_DERIVED_DATA": "work/MacCatalyst" if lane == 1 else f"work/MacCatalyst-lane{lane}"}
    while count < limit:
        if stop_file.exists() and stop_file.stat().st_mtime > started.timestamp():
            reason = "STOP file found"
            break
        if until and any(t["id"] == until and t["state"] == "done" for t in task_queue.load()["tasks"]):
            reason = f"{until} is done"
            break
        if "--dry-run" in argv:
            queue = task_queue.load()
            states = {t["id"]: t["state"] for t in queue["tasks"]}
            task = next((t for t in queue["tasks"] if ready(t, states)), None)
            log(directory, {"event": "dry-run", "lane": lane, "would_take": task and task["id"]})
            reason = "dry run"
            break
        total, strong = runs_today()
        if total >= DAILY_RUNS:
            reason = f"daily Codex run limit reached ({total} runs today)"
            break
        task, others_working = claim(lane)
        if task is not None and model_for(task) == MODELS["strong"] and strong >= DAILY_STRONG_RUNS:
            # Out of strong-model runs for today: hand the task back for tomorrow.
            run([str(PYTHON), "-m", "tools.claw", "queue", "reopen", task["id"], "dispatcher: daily strong-model run limit reached"])
            time.sleep(WAIT_SECONDS)
            continue
        if task is None:
            if others_working:
                time.sleep(WAIT_SECONDS)
                continue
            reason = "no ready task for agents"
            break
        model, effort = model_for(task)
        prompt = PROMPT.format(root=ROOT, id=task["id"], title=task["title"],
                               app_rules=APP_RULES if serial(task) or exclusive(task) else NO_APP)
        count += 1
        log(directory, {"event": "start", "lane": lane, "n": count, "task": task["id"], "model": model, "effort": effort,
                        "at": datetime.datetime.now().strftime("%H:%M")})
        began = time.monotonic()
        command = ["nice", "-n", "10", "codex", "exec", "-m", model, "-c", f"model_reasoning_effort={effort}", "-s", "danger-full-access",
                   "-C", str(ROOT), "-o", str(directory / f"{count:03d}-{task['id']}.last.md"), prompt]
        with open(directory / f"{count:03d}-{task['id']}.log", "w") as output:
            try:
                exit_code = subprocess.run(command, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT,
                                           timeout=TASK_TIMEOUT, env=environment).returncode
            except subprocess.TimeoutExpired:
                exit_code = "timeout"
        state = next(t for t in task_queue.load()["tasks"] if t["id"] == task["id"])
        record = {"event": "end", "lane": lane, "n": count, "task": task["id"], "state": state["state"], "exit": exit_code,
                  "minutes": round((time.monotonic() - began) / 60, 1),
                  "note": (state.get("result") or state.get("needs") or "")[:300]}
        flagged = "flagged for possible cybersecurity risk" in (directory / f"{count:03d}-{task['id']}.log").read_text(errors="ignore")
        if flagged and state["state"] in ("open", "taken"):
            # OpenAI's filter stopped the run; a retry is stopped the same way, so block once and let the owner decide.
            run([str(PYTHON), "-m", "tools.claw", "queue", "start", task["id"]])
            run([str(PYTHON), "-m", "tools.claw", "queue", "block", task["id"], "dispatcher: stopped by OpenAI's cybersecurity filter; owner decides whether Claude takes it"])
            record["dispatcher"] = "blocked by the content filter"
            state = next(t for t in task_queue.load()["tasks"] if t["id"] == task["id"])
        elif state["state"] in ("open", "taken"):
            unrecorded[task["id"]] = unrecorded.get(task["id"], 0) + 1
            if state["state"] == "taken":
                run([str(PYTHON), "-m", "tools.claw", "queue", "reopen", task["id"], "dispatcher: the run ended without recording a result"])
            if unrecorded[task["id"]] >= 2:
                run([str(PYTHON), "-m", "tools.claw", "queue", "start", task["id"]])
                run([str(PYTHON), "-m", "tools.claw", "queue", "block", task["id"], "dispatcher: two runs ended without recording a result"])
                record["dispatcher"] = "blocked after two unrecorded runs"
        # Escalate only a cheaper run that left no result; a recorded block names its follow-up and needs no retry.
        if model == MODELS["cheaper"][0] and state["state"] in ("open", "taken") and not flagged:
            with task_queue.locked():
                queue = task_queue.load()
                states = {t["id"]: t["state"] for t in queue["tasks"]}
                saved = next(t for t in queue["tasks"] if t["id"] == task["id"])
                waits = [d for d in saved.get("depends_on", []) if states.get(d, "done") != "done"]
                if not waits and not saved.get("escalated"):
                    saved.pop("claimed_by", None)
                    saved.update(state="open", escalated=True,
                                 reopen_reason="dispatcher: cheaper run did not finish; retry on the strong model")
                    task_queue.save(queue)
                    record["dispatcher"] = "escalated to the strong model"
                    state = saved
        if exclusive(task) and state["state"] == "done":
            # A harness change makes earlier admissions stale; re-gate them while the other lanes are drained.
            REGATING.touch()
            try:
                regated = run([str(PYTHON), "-m", "tools.claw.regate_stale", "--jobs", "2"])
            finally:
                REGATING.unlink(missing_ok=True)
            try:
                record["regate"] = json.loads(regated.stdout.strip().splitlines()[-1])
            except (IndexError, ValueError):
                record["regate"] = {"status": "error"}
        log(directory, record)
        # A block that only waits on queued prerequisites is the normal split, not a failure.
        queue_now = task_queue.load()
        states_now = {t["id"]: t["state"] for t in queue_now["tasks"]}
        saved_now = next(t for t in queue_now["tasks"] if t["id"] == task["id"])
        waiting = any(states_now.get(d, "done") != "done" for d in saved_now.get("depends_on", []))
        blocked_in_a_row = blocked_in_a_row + 1 if state["state"] == "blocked" and not waiting else 0
        if blocked_in_a_row >= 2:
            reason = "two tasks in a row ended blocked"
            break
        if count % 5 == 0:
            checks = health(since)
            log(directory, {"event": "health", "after": count, **checks})
            if any(v != "pass" for v in checks.values()):
                reason = f"health check failed: {checks}"
                break
    log(directory, {"event": "stop", "lane": lane, "reason": reason, "tasks_run": count,
                    "hours": round((datetime.datetime.now() - started).total_seconds() / 3600, 2)})
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
