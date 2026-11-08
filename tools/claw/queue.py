"""The task queue. One bounded task per agent session. One JSON line.

    python -m tools.claw.queue next              the first open task
    python -m tools.claw.queue list              every task with its state
    python -m tools.claw.queue start <id>        mark a task taken
    python -m tools.claw.queue finish <id> "<one-sentence result>"
    python -m tools.claw.queue block <id> "<what is needed>"

The queue lives in tools/queue.json. The coordinator adds tasks; any agent may take, finish or block one.
"""
import contextlib
import datetime
import fcntl
import json
import sys

from .paths import ROOT

QUEUE = ROOT / "tools" / "queue.json"


@contextlib.contextmanager
def locked():
    """Serialize read-modify-write of the queue between dispatcher lanes and sessions."""
    with open(ROOT / "work" / "queue.lock", "a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def load():
    return json.loads(QUEUE.read_text())


def save(queue):
    QUEUE.write_text(json.dumps(queue, indent=2) + "\n")


def find(queue, task_id):
    for task in queue["tasks"]:
        if task["id"] == task_id:
            return task
    raise SystemExit(json.dumps({"command": "queue", "status": "error", "detail": f"no task {task_id!r}"}))


def main(argv):
    with locked():
        return act(argv)


def act(argv):
    queue = load()
    action = argv[0] if argv else "next"
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    if action == "next":
        task = next((t for t in queue["tasks"] if t["state"] == "open" and t["model"] != "owner"), None)
        waiting = [t["id"] for t in queue["tasks"] if t["state"] == "open" and t["model"] == "owner"]
        print(json.dumps({"command": "queue-next", "task": task, "waiting_for_owner": waiting,
                          "status": "pass" if task else "empty"}))
        return 0
    if action == "list":
        for task in queue["tasks"]:
            print(f"{task['state']:8s} {task['id']:28s} {task['model']:8s} {task['title']}")
        counts = {}
        for task in queue["tasks"]:
            counts[task["state"]] = counts.get(task["state"], 0) + 1
        print(json.dumps({"command": "queue-list", "counts": counts, "status": "pass"}))
        return 0
    task = find(queue, argv[1])
    note = argv[2].strip() if len(argv) > 2 else ""
    if action in ("finish", "block", "reopen") and not note:
        raise SystemExit(json.dumps({"command": f"queue-{action}", "status": "error",
                                     "detail": "give one sentence: what is now true, or what is needed"}))
    if action == "start":
        if task["state"] == "taken" and task.get("claimed_by"):
            print(json.dumps({"command": "queue-start", "task": task["id"], "state": "taken",
                              "detail": f"already claimed for you by {task['claimed_by']}", "status": "pass"}))
            return 0
        if task["state"] != "open":
            raise SystemExit(json.dumps({"command": "queue-start", "status": "error",
                                         "detail": f"{task['id']} is {task['state']}, not open"}))
        task.update(state="taken", taken=stamp)
    elif action == "reopen":
        task.pop("claimed_by", None)
        task.update(state="open", reopened=stamp, reopen_reason=note)
    elif action == "finish":
        task.update(state="done", finished=stamp, result=note)
    elif action == "block":
        task.update(state="blocked", blocked=stamp, needs=note)
    else:
        raise SystemExit(json.dumps({"command": "queue", "status": "error", "detail": f"unknown action {action}"}))
    save(queue)
    print(json.dumps({"command": f"queue-{action}", "task": task["id"], "state": task["state"], "status": "pass"}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
